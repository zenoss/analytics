##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import math
import time


class StateStatistics(object):
    def __init__(self, state):
        self.state = state
        self.reset()

    def addCall(self, elapsedTime):
        self.totalElapsedTime += elapsedTime
        self.totalElapsedTimeSquared += elapsedTime**2
        self.totalCalls += 1

        if self.totalCalls == 1:
            self.minElapsedTime = elapsedTime
            self.maxElapsedTime = elapsedTime
        else:
            self.minElapsedTime = min(self.minElapsedTime, elapsedTime)
            self.maxElapsedTime = max(self.maxElapsedTime, elapsedTime)

    def reset(self):
        self.totalElapsedTime = 0.0
        self.totalElapsedTimeSquared = 0.0
        self.totalCalls = 0
        self.minElapsedTime = 0xFFFFFFFF
        self.maxElapsedTime = 0

    @property
    def mean(self):
        return float(self.totalElapsedTime) / float(self.totalCalls)

    @property
    def stddev(self):
        if self.totalCalls == 1:
            return 0
        else:
            # see http://www.dspguide.com/ch2/2.htm for stddev of running stats
            mean = self.totalElapsedTime**2 / self.totalCalls
            return math.sqrt(
                (self.totalElapsedTimeSquared - mean) / (self.totalCalls - 1)
            )


class TaskStatistics(object):
    def __init__(self, task):
        self.task = task
        self.totalRuns = 0
        self.failedRuns = 0
        self.missedRuns = 0
        self.states = {}
        self.stateStartTime = None

    def trackStateChange(self, oldState, newState):
        now = time.time()

        # record how long we spent in the previous state, if there was one
        if oldState is not None and self.stateStartTime:
            # TODO: how do we properly handle clockdrift or when the clock
            # changes, or is time.time() independent of that?
            elapsedTime = now - self.stateStartTime

            if oldState in self.states:
                stats = self.states[oldState]
            else:
                stats = StateStatistics(oldState)
                self.states[oldState] = stats
            stats.addCall(elapsedTime)

        self.stateStartTime = now
