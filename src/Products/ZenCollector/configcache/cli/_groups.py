##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

from collections import defaultdict
from itertools import chain

import attr

from ._stats import UniqueCountStat


class DeviceGroup(object):

    name = "devices"
    order = 1

    def __init__(self, stats):
        # Only one row, so use summary
        self._summary = tuple(s() for s in stats)
        try:
            # DeviceGroup doesn't want CountStat
            posn = stats.index(UniqueCountStat)
        except ValueError:
            # Not found, so don't worry about it
            self._counter = None
            self._otherstats = self._summary
        else:
            # Found, replace it with UniqueCountStat
            self._counter = self._summary[posn]
            self._otherstats = self._summary[0:posn] + self._summary[posn+1:]
        self._stats = stats
        self._samples = 0

    def handle_key(self, key):
        if self._counter is None:
            return
        self._counter.mark(key.device)
        self._samples += 1

    def handle_timestamp(self, key, ts):
        for stat in self._otherstats:
            stat.mark(ts)
        self._samples += 1

    def handle_status(self, status):
        pass

    def headings(self):
        return [s.name for s in self._stats]

    def hints(self):
        return [s.type_ for s in self._stats]

    def rows(self):
        return []

    def summary(self):
        if self._samples == 0:
            return []
        return [s.value() for s in self._summary]


class ServiceGroup(object):

    name = "services"
    order = 2

    def __init__(self, stats):
        self._stats = stats
        self._byrow = defaultdict(self._makerowvalue)
        self._summary = tuple(s() for s in stats)
        self._samples = 0

    def _makerowvalue(self):
        return tuple(stat() for stat in self._stats)

    def handle_key(self, key):
        pass

    def handle_timestamp(self, key, ts):
        for stat in self._byrow[key.service]:
            stat.mark(ts)
        for stat in self._summary:
            stat.mark(ts)
        self._samples += 1

    def handle_status(self, status):
        pass

    def headings(self):
        headings = ["configuration service class"]
        headings.extend(s.name for s in self._stats)
        return headings

    def hints(self):
        hints = ["str"]
        hints.extend(s.type_ for s in self._stats)
        return hints

    def rows(self):
        if self._samples == 0:
            return []
        return (
            self._makerow(svcname, stats)
            for svcname, stats in self._byrow.iteritems()
        )

    def _makerow(self, svcname, stats):
        return tuple(chain((svcname,), (s.value() for s in stats)))

    def summary(self):
        if self._samples == 0:
            return []
        return [s.value() for s in self._summary]


class MonitorGroup(object):

    name = "monitors"
    order = 3

    def __init__(self, stats):
        self._stats = stats
        self._byrow = defaultdict(self._makerowvalue)
        self._summary = tuple(s() for s in stats)
        self._samples = 0

    def _makerowvalue(self):
        return tuple(stat() for stat in self._stats)

    def handle_key(self, key):
        pass

    def handle_timestamp(self, key, ts):
        for stat in self._byrow[key.monitor]:
            stat.mark(ts)
        for stat in self._summary:
            stat.mark(ts)
        self._samples += 1

    def handle_status(self, status):
        pass

    def headings(self):
        headings = ["collector"]
        headings.extend(s.name for s in self._stats)
        return headings

    def hints(self):
        hints = ["str"]
        hints.extend(s.type_ for s in self._stats)
        return hints

    def rows(self):
        if self._samples == 0:
            return []
        return (
            self._makerow(name, stats)
            for name, stats in self._byrow.iteritems()
        )

    def _makerow(self, name, stats):
        return tuple(chain((name,), (s.value() for s in stats)))

    def summary(self):
        if self._samples == 0:
            return []
        return [s.value() for s in self._summary]


class StatusGroup(object):

    name = "statuses"
    order = 4

    def __init__(self, stats):
        self._stats = stats
        self._byrow = defaultdict(self._makerowvalue)
        self._summary = tuple(s() for s in stats)
        self._samples = 0

    def _makerowvalue(self):
        return tuple(stat() for stat in self._stats)

    def handle_key(self, key):
        pass

    def handle_timestamp(self, key, ts):
        pass

    def handle_status(self, status):
        data = attr.astuple(status)
        for stat in self._byrow[type(status).__name__]:
            stat.mark(data[-1])
        for stat in self._summary:
            stat.mark(data[-1])
        self._samples += 1

    def headings(self):
        headings = ["status"]
        headings.extend(s.name for s in self._stats)
        return headings

    def hints(self):
        hints = ["str"]
        hints.extend(s.type_ for s in self._stats)
        return hints

    def rows(self):
        if self._samples == 0:
            return []
        return (
            self._makerow(name, stats)
            for name, stats in self._byrow.iteritems()
        )

    def _makerow(self, name, stats):
        return tuple(chain((name,), (s.value() for s in stats)))

    def summary(self):
        if self._samples == 0:
            return []
        return [s.value() for s in self._summary]
