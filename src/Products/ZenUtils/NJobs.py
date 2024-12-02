#! /usr/bin/env python 
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''NJobs

Run a list of jobs in parallel, limited to N at a time.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.internet import reactor, defer


class NJobs:
    "Run a list of jobs in parallel, limited to N at a time."
    
    def __init__(self, max, callable, data):
        self.defer = defer.Deferred()
        self.results = []
        self.max = max
        self.callable = callable
        self.workQueue = data
        self.running = 0

    def start(self):
        self._runSome()
        return self.defer

    def status(self):
        return self.running, len(self.workQueue), len(self.results)

    def _runSome(self):
        while self.running < self.max and self.workQueue:
            self.running += 1
            try:
                d = self.callable(self.workQueue.pop())
            except Exception as ex:
                self._finished(ex)
            else:
                d.addBoth(self._finished)
        if self.running == 0 and not self.workQueue and not self.defer.called:
            self.defer.callback(self.results)

    def _finished(self, result):
        self.running -= 1
        self.results.append(result)
        reactor.callLater(0, self._runSome)
