##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """Step

Utility for chaining defered actions.

"""

from twisted.internet import reactor, defer

def Step(iterable):
    ''' Step through iterable looking for deferreds.  Whenever a deferred is
    encountered wait until it is called before continuing through iterable.
    
    Iterable is usually a generator function that yields a defered
    anytime it wants to wait for that deferred to trigger before
    continuing execution.
    '''
    def doSteps(result):
        # Depending on closure for value of iterable and finalD.
        # If this causes problems we can pass them as arguments
        # to doSteps and pass them in the addCallback(doSteps..) call.
        #
        # We don't actually use result anywhere here unless we are done
        # iterating through iterable, in which case result becomes the
        # result for the finalD deferred.
        # Code within the iterable that needs the result of the previously
        # yielded defered can get it directly from that deferred's result
        # attribute.
        for result in iterable:
            # Keep getting items from iterable (the generator) until
            # one returns a deferred.  Then add this function as a 
            # callback to that deferred and return from the function.
            if isinstance(result, defer.Deferred):
                result.addCallback(doSteps)
                return result
        finalD.callback(result)
        return result
    
    # Make sure we have an iterable
    if not hasattr(iterable, 'next'):
        if hasattr(iterable, '__iter__'):
            iterable = iter(iterable)
        else:
            raise RuntimeError( 'Must pass an iterable object to step' )
            
    # finalD is the deferred that will trigger when iterable is exhausted
    finalD = defer.Deferred()
    
    # start consuming the iterable
    doSteps(None)
    
    return finalD


class Test:

    def foo(self, n):
        d  = defer.Deferred()
        reactor.callLater(2, d.callback, n)
        return d


    def sequence(self):
        d1 = self.foo(1)
        print 'yielding d1 from sequence'
        yield d1
        r1 = d1.result
        d2 = self.foo(r1 + 1)
        print 'yielding d2 from sequence'
        yield d2
        r2 = d2.result
        print 'yielding final result from sequence'
        yield r2


    def myCallback(self, r):
        print 'final deferred returned %s' % `r`


    def go(self):
        myD = Step(self.sequence())
        myD.addCallback(self.myCallback)
        reactor.callLater(10, reactor.stop)
        reactor.run()
