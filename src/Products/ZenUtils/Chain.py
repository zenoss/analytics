#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''Chain

Chain a series of deferred actions serially.

$Id$
'''

__version__ = "$Revision$"[11:-2]



from twisted.internet import defer

class Chain:
    """Call a function over an interable of data, after each finishes."""

    def __init__(self, callable, iterable):
        self.callable = callable
        self.iterable = iterable
        self.results = []
        self.defer = defer.Deferred()

    def run(self):
        self.next()
        return self.defer

    def next(self):
        "run the next step"
        try:
            next = self.iterable.next()
            self.callable(next).addCallbacks(self.success, self.failure)
        except StopIteration:
            self.defer.callback(self.results)
        except Exception as ex:
            self.failure(ex)

    def success(self, result):
        "gather a successful result"
        self.results.append((True, result))
        self.next()

    def failure(self, result):
        "gather an error result"
        self.results.append((False, result))
        self.next()
