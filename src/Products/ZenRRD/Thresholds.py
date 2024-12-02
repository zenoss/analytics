##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.thresholds")


class Thresholds(object):
    """Class for holding multiple Thresholds, used in most collectors."""

    def __init__(self):
        self.byKey = {}
        self.byContextKey = {}
        self.byDevice = {}

    def _contextKey(self, contextKey, dp):
        return "%s/%s" % (contextKey, dp.rsplit("/", 1)[-1])

    def remove(self, threshold):
        d = self.byDevice.get(threshold.context().deviceName, None)
        if d and threshold.key() in d:
            del d[threshold.key()]
        doomed = self.byKey.get(threshold.key(), None)
        if doomed:
            del self.byKey[doomed.key()]
            ctx = doomed.context()
            for dp in doomed.dataPoints():
                contextKey = self._contextKey(ctx.contextKey, dp)
                lst = self.byContextKey[contextKey]
                if (doomed, dp) in lst:
                    lst.remove((doomed, dp))
                if not lst:
                    del self.byContextKey[contextKey]
        return doomed

    def add(self, threshold):
        self.byKey[threshold.key()] = threshold
        d = self.byDevice.setdefault(threshold.context().deviceName, {})
        d[threshold.key()] = threshold
        ctx = threshold.context()
        for dp in threshold.dataPoints():
            self.byContextKey.setdefault(
                self._contextKey(ctx.contextKey, dp), []
            ).append((threshold, dp))

    def update(self, threshold):
        "Store a threshold instance for future computation"
        log.debug("Updating threshold %r", threshold.key())
        doomed = self.remove(threshold)
        if doomed:
            threshold.count = doomed.count
        self.add(threshold)

    def updateList(self, thresholds):
        "Store a threshold instance for future computation"
        for threshold in thresholds:
            self.update(threshold)

    def thresholdsForDevice(self, device):
        return self.byDevice.get(device, {}).values()

    def updateForDevice(self, device, thresholds):
        "Store a threshold instance for future computation"
        doomed = dict((d.key(), d) for d in self.thresholdsForDevice(device))
        self.updateList(thresholds)
        for threshold in thresholds:
            if threshold.key() in doomed:
                del doomed[threshold.key()]
        for d in doomed.values():
            self.remove(d)

    def check(self, contextId, datapoint, timeAt, value):
        "Check a given threshold based on an updated value"
        result = []
        contextKey = self._contextKey(contextId, datapoint)
        if contextKey in self.byContextKey:
            log.debug("Checking value %s on %s", value, contextKey)
            for t, dp in self.byContextKey[contextKey]:
                events = t.checkValue(dp, timeAt, value)
                if events:
                    result.extend(events)
        return result
