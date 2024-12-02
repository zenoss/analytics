##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging

from twisted.spread import pb

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenEvents.ZenEventClasses import Status_IpService
from Products.ZenModel.Service import Service
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer

log = logging.getLogger("zen.ZenStatusConfig")


class ServiceProxy(pb.Copyable, pb.RemoteCopy):
    """
    Represents a service component. A single DeviceProxy config will have
    multiple service proxy components (for each service zenstatus should
    monitor)
    """

    def __init__(self, svc, status):
        self.device = svc.hostname()
        self.component = svc.name()
        self.ip = svc.getManageIp()
        self.port = svc.getPort()
        self.sendString = svc.getSendString()
        self.expectRegex = svc.getExpectRegex()
        self.timeout = svc.zStatusConnectTimeout
        self.failSeverity = svc.getFailSeverity()
        self.status = status
        self.key = svc.key()
        self.deviceManageIp = svc.device().manageIp

    def __str__(self):
        return " ".join(map(str, [self.device, self.component, self.port]))


pb.setUnjellyableForClass(ServiceProxy, ServiceProxy)

TCP_PROTOCOLS = set(["tcp", "tcp4"])


class ZenStatusConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        # Any additional attributes we want to send to daemon should be
        # added here
        deviceProxyAttributes = ()
        CollectorConfigService.__init__(
            self, dmd, instance, deviceProxyAttributes
        )

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)
        hasTcpComponents = False
        if include:
            for svc in device.getMonitoredComponents(collector="zenstatus"):
                if svc.getProtocol() in TCP_PROTOCOLS:
                    hasTcpComponents = True
                    break

        return include and hasTcpComponents

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)
        proxy.configCycleInterval = self.conf.statusCycleInterval

        # add each component
        proxy.components = []
        for svc in device.getMonitoredComponents(collector="zenstatus"):
            if svc.getProtocol() in TCP_PROTOCOLS:
                # get component status
                status = svc.getStatus(Status_IpService)
                proxy.components.append(ServiceProxy(svc, status))

        # don't bother adding this device proxy if there aren't any services
        # to monitor
        if not proxy.components:
            log.debug(
                "Device %s skipped because there are no components", proxy.id
            )
            return None

        return proxy

    def _getNotifiableClasses(self):
        """
        When zProperties are changed on either of these two classes we
        need to refresh which devices we are monitoring
        """
        return (Service, ServiceOrganizer)


if __name__ == "__main__":
    from Products.ZenHub.ServiceTester import ServiceTester

    tester = ServiceTester(ZenStatusConfig)

    def printer(proxy):
        print("\t".join(["", "Hostname", "Service name", "Port"]))
        for component in proxy.components:
            print("\t", component)

    tester.printDeviceProxy = printer
    tester.showDeviceInfo()
