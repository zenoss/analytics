##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''Driver.py

Run generators that produce Deferreds.

twisted.flow has something like this, except I cannot understand it.

$Id$
'''

__version__ = "$Revision$"[11:-2]


from twisted.internet import defer, reactor
from twisted.python import failure
from Products.ZenUtils.Exceptions import resolveException


class ShortCircuit:
    def __init__(self, value):
        self.value = value

class Driver:
    "Walk an iterable that returns a deferred."
    
    def __init__(self):
        self.defer = defer.Deferred()
        self.result = None

    def drive(self, iterable):
        "Call the iterable and set up callbacks to finish"
        self.iter = iterable
        self._next()
        return self.defer

    def _next(self):
        "Move on to the next iterable value"
        try:
            self.iter.next().addBoth(self._finish)
        except StopIteration:
            self.defer.callback(self.result)
        except ShortCircuit as ex:
            self.result = ex.value
            self.defer.callback(self.result)
        except Exception as ex:
            self.defer.errback(failure.Failure(ex))

    def result(self):
        "Provide the result of the iterable as a value or exception"
        ex = self.result
        if isinstance(self.result, failure.Failure):
            ex = resolveException(self.result)
        if isinstance(ex, Exception):
            raise ex
        return self.result
    next = result                       # historical name for result

    def finish(self, result):
        raise ShortCircuit(result)

    def _finish(self, result):
        "Store the result of the last deferred for use in next()"
        self.result = result
        # prevent endless recursion
        reactor.callLater(0, self._next)

def drive(callable):
    '''Typical use of Driver class:

    def walk(driver):
        yield thing1()
        a = driver.next()
        print "Thing 1 is", 
        yield thing2()
        b = driver.next()
        print "Thing 2 is", 
        driver.finish(a + b)

    drive(walk)

    '''
    d = Driver()
    return d.drive(callable(d))


def driveLater(secs, callable):
    "Drive the callable at a later time"
    d = defer.Deferred()
    def driveAgain():
        drive(callable).chainDeferred(d)
    reactor.callLater(secs, driveAgain)
    return d


def test():
    lst = []
    def loop(d):
        for i in range(10):
            yield defer.succeed(i)
            lst.append(d.next())
    def final(v):
        assert lst[-1] == v
        assert lst == range(10)
        def unloop(d):
            yield defer.fail(ZeroDivisionError('hahaha'))
            d.next()
        def checkError(err):
            assert isinstance(err.value, ZeroDivisionError)
            reactor.stop()
        drive(unloop).addErrback(checkError)
    drive(loop).addCallback(final)
        

if __name__ == '__main__':
    test()
    reactor.run()
