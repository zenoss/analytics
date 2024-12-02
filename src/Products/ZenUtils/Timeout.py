##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.internet import reactor
from twisted.internet import defer

class TimeoutDeferred(defer.Deferred):
    """A deferred that fires errback if the result doesn't come
    back in the given time period"""

    timer = None
    
    def __init__(self, other, timeout):
        """Wrap the passed deferred and return a new deferred that
        will timeout

        @type other: a Deferred
        @param other: the deferred to wrap
        @type timeout: floating point number
        @param timeout: time, in seconds, to wait before failing the deferred
        """
        defer.Deferred.__init__(self)
        self.timer = reactor.callLater(timeout, self._timeout)
        other.chainDeferred(self)

    def _timeout(self):
        "The wrapped deferred was too slow: fire the errback"
        if not self.called:
            self.timer = None
            self.errback(defer.TimeoutError())

    def _startRunCallbacks(self, result):
        "We have a result, fire callbacks or cancel the timer"
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if not self.called:
            defer.Deferred._startRunCallbacks(self, result)

def timeout(deferred, timeInSeconds):
    "Utility method to wrap a deferred to timeout in timeInSeconds"
    return TimeoutDeferred(deferred, timeInSeconds)
