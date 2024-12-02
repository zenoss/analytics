##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
from fnmatch import fnmatch
from zope.component import createObject
from zope.interface import implementer
from Products.Zuul.interfaces import IMonitorFacade, IInfo

LOG = logging.getLogger("Zuul.facades")


@implementer(IMonitorFacade)
class MonitorFacade(object):
    """
    """

    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._perf = self._dmd.Monitors.Performance

    def query(self, name=None):
        """
        Returns a sequence of IMonitor objects.
        """
        namePattern = name if (name is not None) else "*"
        monitors = []
        for name in self._perf.getPerformanceMonitorNames():
            if fnmatch(name, namePattern):
                monitor = self._perf.get(name).primaryAq()
                monitors.append(monitor)
        return monitors

    def get(self, monitorId, default=None):
        """
        Returns the IMonitor object of the identified application.
        """
        return self._perf.get(monitorId, default)

    def add(self, monitorId, sourceId=None):
        """
        """
        createObject("PerformanceConf", self._perf, monitorId, sourceId)
        monitor = self._perf.get(monitorId)
        return monitor

    def delete(self, monitorId):
        """
        """
        if monitorId in list(self._perf.getPerformanceMonitorNames()):
            self._perf.manage_removeMonitor(ids=(monitorId,))
