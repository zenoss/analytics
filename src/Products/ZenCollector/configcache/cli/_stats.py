##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

import sys
import time

_current_time = None


def _current_time_unset():
    global _current_time
    _current_time = time.time()
    try:
        return _current_time
    finally:
        global _get_current_time
        _get_current_time = _current_time_set


def _current_time_set():
    global _current_time
    return _current_time


_get_current_time = _current_time_unset


class CountStat(object):

    name = "count"
    type_ = "int"

    def __init__(self):
        self._count = 0

    def mark(self, *args):
        self._count += 1

    def value(self):
        return self._count


class UniqueCountStat(CountStat):

    name = "count of devices"

    def __init__(self):
        self._values = set()

    def mark(self, value):
        self._values.add(value)

    def value(self):
        return len(self._values)


class AverageStat(object):

    name = "average"
    type_ = "timedelta"

    def __init__(self):
        self._total = 0
        self._count = 0

    def mark(self, value):
        self._count += 1
        self._total += value

    def value(self):
        if self._count == 0:
            return 0
        return self._total / self._count


class AverageAgeStat(AverageStat):

    name = "average age"

    def value(self):
        avg = super(AverageAgeStat, self).value()
        if avg == 0:
            return 0
        return _get_current_time() - avg


class MedianStat(object):

    name = "median"
    type_ = "timedelta"

    def __init__(self):
        self._min = sys.maxsize
        self._max = 0

    def mark(self, value):
        value = int(value)
        self._min = min(self._min, value)
        self._max = max(self._max, value)

    def value(self):
        if self._min == sys.maxsize:
            return 0
        return (self._min + self._max) / 2


class MedianAgeStat(MedianStat):

    name = "median age"

    def value(self):
        median = super(MedianAgeStat, self).value()
        if median == 0:
            return 0
        return _get_current_time() - median


class MinStat(object):

    name = "min"
    type_ = "float"

    def __init__(self):
        self._min = sys.maxsize

    def mark(self, value):
        self._min = min(self._min, int(value))

    def value(self):
        if self._min == sys.maxsize:
            return 0
        return self._min


class MaxAgeStat(MinStat):

    name = "max age"
    type_ = "timedelta"

    def value(self):
        maxv = super(MaxAgeStat, self).value()
        if maxv == 0:
            return 0
        return _get_current_time() - maxv


class MaxStat(object):

    name = "max"
    type_ = "float"

    def __init__(self):
        self._max = 0

    def mark(self, value):
        self._max = max(self._max, int(value))

    def value(self):
        if self._max == 0:
            return 0
        return self._max


class MinAgeStat(MaxStat):

    name = "min age"
    type_ = "timedelta"

    def value(self):
        minv = super(MinAgeStat, self).value()
        if minv == 0:
            return 0
        return _get_current_time() - minv
