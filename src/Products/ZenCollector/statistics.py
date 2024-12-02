##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component.factory import Factory
from zope.interface import implementer

from .interfaces import IStatistic, IStatisticsService


@implementer(IStatistic)
class Statistic(object):
    def __init__(self, name, type, **kwargs):
        self.value = 0
        self.name = name
        self.type = type
        self.kwargs = kwargs


@implementer(IStatisticsService)
class StatisticsService(object):
    def __init__(self):
        self._stats = {}

    def addStatistic(self, name, type, **kwargs):
        if name in self._stats:
            raise NameError("Statistic %s already exists" % name)

        if type not in ("DERIVE", "COUNTER", "GAUGE"):
            raise TypeError("Statistic type %s not supported" % type)

        stat = Statistic(name, type, **kwargs)
        self._stats[name] = stat

    def getStatistic(self, name):
        return self._stats[name]

    def postStatistics(self, rrdStats):
        for stat in self._stats.values():
            # figure out which function to use to post this statistical data
            try:
                func = {
                    "COUNTER": rrdStats.counter,
                    "GAUGE": rrdStats.gauge,
                    "DERIVE": rrdStats.derive,
                }[stat.type]
            except KeyError:
                raise TypeError("Statistic type %s not supported" % stat.type)

            # These should always come back empty now because DaemonStats
            # posts the events for us
            func(stat.name, stat.value, **stat.kwargs)

            # counter is an ever-increasing value, but otherwise...
            if stat.type != "COUNTER":
                stat.value = 0


class StatisticsServiceFactory(Factory):
    """Factory for StatisticsService objects."""

    def __init__(self):
        super(StatisticsServiceFactory, self).__init__(
            StatisticsService,
            "StatisticsService",
            "Creates a StatisticsService instance",
        )
