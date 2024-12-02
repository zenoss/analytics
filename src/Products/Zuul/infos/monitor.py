##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.component import adapter
from zope.interface import implementer

from Products.ZenModel.interfaces import IMonitor
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.Zuul.interfaces import IMonitorInfo, IMonitorTreeNode
from Products.Zuul.infos import ProxyProperty, InfoBase


@adapter(IMonitor)
@implementer(IMonitorTreeNode)
class MonitorTreeNode(object):
    """
    """

    def __init__(self, context, root=None, parent=None):
        """
        """
        self._ctx = context  # references the dmd node
        self._children = []

    @property
    def type(self):
        return  "collector" if isinstance(self._ctx, PerformanceConf) else "hub"

    @property
    def id(self):
        # get full zodb path
        return '.'.join(self._ctx.getPhysicalPath())

    @property
    def path(self):
        # Return the path relative to the organizer
        return '/'.join(self._ctx.getPhysicalPath())

    uid = path

    @property
    def name(self):
        # get full zodb path
        return self._ctx.id

    @property
    def text(self):
        # Name of the monitor
        return self._ctx.id

    @property
    def leaf(self):
        return False

    def addChild(self, child):
        self._children.append(child)

    @property
    def children(self):
        return self._children

    @property
    def devcount(self):
        if self.type == "collector":
            return self._ctx.devices.countObjects()
        else:
            return 0


@implementer(IMonitorInfo)
class MonitorInfo(InfoBase):
    """
    """
    eventlogCycleInterval = ProxyProperty('eventlogCycleInterval', convert=int)
    processCycleInterval = ProxyProperty('processCycleInterval', convert=int)
    statusCycleInterval = ProxyProperty('statusCycleInterval', convert=int)
    winCycleInterval = ProxyProperty('winCycleInterval', convert=int)
    wmibatchSize = ProxyProperty('wmibatchSize', convert=int)
    wmiqueryTimeout = ProxyProperty('wmiqueryTimeout', convert=int)
    configCycleInterval = ProxyProperty('configCycleInterval', convert=int)
    zenProcessParallelJobs = ProxyProperty('zenProcessParallelJobs', convert=int)
    pingTimeOut = ProxyProperty('pingTimeOut', convert=float)
    pingTries = ProxyProperty('pingTries', convert=int)
    pingCycleInterval = ProxyProperty('pingCycleInterval', convert=int)
    modelerCycleInterval = ProxyProperty('modelerCycleInterval', convert=int)

    @property
    def discoveryNetworks(self):
        return ",".join(self._object.discoveryNetworks)

    @discoveryNetworks.setter
    def discoveryNetworks(self, value):
        self._object.discoveryNetworks = value.split(",")
