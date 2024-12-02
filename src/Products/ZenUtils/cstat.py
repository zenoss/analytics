##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""cstat.py provides efficient utilities to compute performance
metrics in memory.
"""

import time
import itertools

class CStat(object):
    """
    CStat is a circular buffer for storing statistics. Values are placed
    in to 1 second buckets using a customizable operator (default is 
    increment). CStat clears buckets as the 1s timestamp window moves.
    """

    def __init__(self, capacity, defaultValue=0, op=lambda x,y: x+y):
        self._capacity = capacity
        self._last = 0
        self._lastBucket = 0
        self._op = op
        self._defaultValue = defaultValue
        self._buffer = [self._defaultValue] * self._capacity

    def _getBucket(self, ts):
        """
        _getBucket() returns an integer timestamp as well as the 
        bucket the ts aligns to.
        """
        if ts is None:
            ts = time.time()
        current = int(ts)
        return current, current % self._capacity 

    def _clearGap(self, current, currentBucket):

        # clear all buckets between lastBucket and current
        diff = current - self._last
        if diff >= self._capacity:
            gap = self._capacity
        else:
            # micro optimization, no need to clear gap if 
            # current and last buckets are the same
            if currentBucket == self._lastBucket:
                return
            gap = (current - self._last) % self._capacity
        for i in xrange(currentBucket, currentBucket - gap, -1):
            self._buffer[i] = self._defaultValue

    def save(self, value, ts=None):
        """
        save() stores the value in the current bucket using 
        the self._op function.
        """
        current, currentBucket = self._getBucket(ts)
        self._clearGap(current, currentBucket)
        self._last, self._lastBucket = current, currentBucket

        self._buffer[currentBucket] = self._op(self._buffer[currentBucket], value)

    def query(self, window, ts=None, op=None):
        """
        query() the buffer over the window and reduce() the dataset using
        op or self._op
        """
        if window > self._capacity:
            raise ValueError("window size can not exceed CStat capacity")

        current, currentBucket = self._getBucket(ts)
        self._clearGap(current, currentBucket)
        self._last, self._lastBucket = current, currentBucket

        if op is None:
            op = self._op

        return reduce(op, map(lambda i: self._buffer[i % self._capacity], xrange(current - window, current)))
