##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from pynetsnmp import usm
from pynetsnmp.twistedsnmp import AgentProxy
from twisted.spread import pb
from zope import component

from Products.ZenHub.errors import translateError
from Products.ZenHub.HubService import HubService
from Products.ZenHub.interfaces import IBatchNotifier
from Products.ZenHub.zodb import onUpdate
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.ZenPack import ZenPack

from .Procrastinator import Procrastinate
from .ThresholdMixin import ThresholdMixin

log = logging.getLogger("zen.performanceconfig")

ATTRIBUTES = (
    "id",
    "manageIp",
    "zMaxOIDPerRequest",
    "zSnmpMonitorIgnore",
    "zSnmpAuthPassword",
    "zSnmpAuthType",
    "zSnmpCommunity",
    "zSnmpCommunities",
    "zSnmpContext",
    "zSnmpDiscoveryPorts",
    "zSnmpPort",
    "zSnmpPrivPassword",
    "zSnmpPrivType",
    "zSnmpSecurityName",
    "zSnmpTimeout",
    "zSnmpTries",
    "zSnmpVer",
    "zSnmpEngineId",
)


class SnmpConnInfo(pb.Copyable, pb.RemoteCopy):
    "A class to transfer the many SNMP values to clients"

    changed = False

    def __init__(self, device):
        "Store the properties from the device"
        for propertyName in ATTRIBUTES:
            setattr(self, propertyName, getattr(device, propertyName, None))
            self.id = device.id

    def __eq__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return False
        if self is other:
            return True
        return all(
            getattr(self, name) == getattr(other, name) for name in ATTRIBUTES
        )

    def __lt__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return NotImplemented
        if self is other:
            return False
        return any(
            getattr(self, name) < getattr(other, name) for name in ATTRIBUTES
        )

    def __le__(self, other):
        if not isinstance(other, SnmpConnInfo):
            return NotImplemented
        if self is other:
            return True
        return not any(
            getattr(self, name) > getattr(other, name) for name in ATTRIBUTES
        )

    def summary(self):
        result = "device=%s peer=%s:%s timeout=%s tries=%d version=%s" % (
            self.id,
            self.manageIp,
            self.zSnmpPort,
            self.zSnmpTimeout,
            self.zSnmpTries,
            self.zSnmpVer,
        )
        if "3" not in self.zSnmpVer:
            result += " community=%s" % self.zSnmpCommunity
        else:
            result += (
                " securityName=%s authType=%s authPassword=%s"
                " privType=%s privPassword=%s engineID=%s"
            ) % (
                self.zSnmpSecurityName,
                self.zSnmpAuthType,
                "****" if self.zSnmpAuthPassword else "",
                self.zSnmpPrivType,
                "****" if self.zSnmpPrivPassword else "",
                "****" if self.zSnmpEngineId else "",
            )
        return result

    def createSession(self, protocol=None):
        """Create a session based on the properties"""
        if "3" in self.zSnmpVer:
            sec = usm.User(
                self.zSnmpSecurityName,
                auth=usm.Authentication(
                    self.zSnmpAuthType, self.zSnmpAuthPassword
                ),
                priv=usm.Privacy(self.zSnmpPrivType, self.zSnmpPrivPassword),
                engine=self.zSnmpEngineId,
                context=self.zSnmpContext,
            )
        else:
            sec = usm.Community(self.zSnmpCommunity, version=self.zSnmpVer)
        p = AgentProxy.create(
            (self.manageIp, self.zSnmpPort),
            security=sec,
            timeout=self.zSnmpTimeout,
            retries=max(self.zSnmpTries - 1, 0),
        )
        p.snmpConnInfo = self
        return p

    def __repr__(self):
        return "<%s for %s>" % (self.__class__, self.id)


pb.setUnjellyableForClass(SnmpConnInfo, SnmpConnInfo)


class PerformanceConfig(HubService, ThresholdMixin):
    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.conf = self.dmd.Monitors.Performance._getOb(self.instance)
        self.procrastinator = Procrastinate(self.pushConfig)
        self._collectorMap = {}
        self._notifier = component.getUtility(IBatchNotifier)

    @translateError
    def remote_propertyItems(self):
        return self.conf.propertyItems()

    @onUpdate(PerformanceConf)
    def perfConfUpdated(self, conf, event):
        if conf.id == self.instance:
            for listener in self.listeners:
                listener.callRemote("setPropertyItems", conf.propertyItems())

    @onUpdate(ZenPack)
    def zenPackUpdated(self, zenpack, event):
        for listener in self.listeners:
            try:
                listener.callRemote(
                    "updateThresholdClasses", self.remote_getThresholdClasses()
                )
            except Exception:
                self.log.warning(
                    "Error notifying a listener of new threshold classes"
                )
