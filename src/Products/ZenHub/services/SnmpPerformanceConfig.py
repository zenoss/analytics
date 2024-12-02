##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

"""SnmpPerformanceConfig

Provides configuration to zenperfsnmp clients.
"""

import re
import logging

from pprint import pformat

from twisted.spread import pb

from Products.ZenCollector.services.config import (
    CollectorConfigService,
    DeviceProxy,
)

log = logging.getLogger("zen.HubService.SnmpPerformanceConfig")


def get_component_manage_ip(component, default=None):
    get_manage_ip = getattr(component, "getManageIp", None)
    if get_manage_ip is None:
        return default
    return get_manage_ip()


class SnmpDeviceProxy(DeviceProxy, pb.Copyable, pb.RemoteCopy):
    def __repr__(self):
        sci = getattr(self, "snmpConnInfo", None)
        scimi = None if (sci is None) else sci.manageIp
        return pformat(
            {
                "id": self.id,
                "_config_id": getattr(self, "_config_id", None),
                "manageIp": self.manageIp,
                "snmpConnInfo.manageIp": scimi,
                "oids": getattr(self, "oids", None),
            }
        )


pb.setUnjellyableForClass(SnmpDeviceProxy, SnmpDeviceProxy)


class SnmpPerformanceConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        deviceProxyAttributes = (
            "zMaxOIDPerRequest",
            "zSnmpMonitorIgnore",
            "zSnmpAuthPassword",
            "zSnmpAuthType",
            "zSnmpCommunity",
            "zSnmpPort",
            "zSnmpPrivPassword",
            "zSnmpPrivType",
            "zSnmpSecurityName",
            "zSnmpTimeout",
            "zSnmpTries",
            "zSnmpVer",
            "zSnmpCollectionInterval",
        )
        CollectorConfigService.__init__(
            self, dmd, instance, deviceProxyAttributes
        )

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)

        if getattr(device, "zSnmpMonitorIgnore", False):
            self.log.debug(
                "Device %s skipped because zSnmpMonitorIgnore is True",
                device.id,
            )
            include = False

        if not device.getManageIp():
            self.log.debug(
                "Device %s skipped because its management "
                "IP address is blank.",
                device.id,
            )
            include = False

        return include

    def _transform_oid(self, oid, comp):
        """lookup the index"""
        index = None
        snmpindex_dct = getattr(comp, "snmpindex_dct", None)
        if snmpindex_dct is not None:
            for prefix, index_ in snmpindex_dct.iteritems():
                if oid.startswith(prefix):
                    index = index_
                    break
        if index is None:
            index = getattr(comp, "ifindex", comp.snmpindex)
        return "{0}.{1}".format(oid, index) if index else oid

    def _getComponentConfig(self, comp, perfServer, oids):
        """
        SNMP components can build up the actual OID based on a base OID and
        the snmpindex of the component.
        """
        if comp.snmpIgnore():
            return None

        validOID = re.compile(r"(?:\.?\d+)+$")
        metadata = comp.getMetricMetadata()
        for templ in comp.getRRDTemplates():
            for ds in templ.getRRDDataSources("SNMP"):
                if not ds.enabled or not ds.oid:
                    continue

                oid = self._transform_oid(ds.oid.strip("."), comp)
                if not oid:
                    log.warn(
                        "The data source %s OID is blank -- ignoring", ds.id
                    )
                    continue
                elif not validOID.match(oid):
                    oldOid = oid
                    oid = self.dmd.Mibs.name2oid(oid)
                    if not oid:
                        msg = "The OID %s is invalid -- ignoring" % oldOid
                        self.sendEvent(
                            dict(
                                device=comp.device().id,
                                component=ds.getPrimaryUrlPath(),
                                eventClass="/Status/Snmp",
                                severity=Warning,
                                summary=msg,
                            )
                        )
                        continue

                for dp in ds.getRRDDataPoints():
                    cname = comp.id
                    oidData = (
                        cname,
                        dp.name(),
                        dp.rrdtype,
                        dp.getRRDCreateCommand(perfServer).strip(),
                        dp.rrdmin,
                        dp.rrdmax,
                        metadata,
                    )

                    # An OID can appear in multiple data sources/data points
                    oids.setdefault(oid, []).append(oidData)

        return comp.getThresholdInstances("SNMP")

    def _createDeviceProxies(self, device):
        manage_ips = {device.manageIp: ([], False)}
        components = device.os.getMonitoredComponents(collector="zenperfsnmp")
        for component in components:
            manage_ip = get_component_manage_ip(component, device.manageIp)
            if manage_ip not in manage_ips:
                log.debug("Adding manage IP %s from %r", manage_ip, component)
                manage_ips[manage_ip] = ([], True)
            manage_ips[manage_ip][0].append(component)
        proxies = []
        for manage_ip, (components, components_only) in manage_ips.items():
            proxy = self._createDeviceProxy(
                device, manage_ip, components, components_only
            )
            if proxy is not None:
                proxies.append(proxy)
        return proxies

    def _createDeviceProxy(
        self, device, manage_ip=None, components=(), components_only=False
    ):
        proxy = SnmpDeviceProxy()
        proxy = CollectorConfigService._createDeviceProxy(self, device, proxy)
        proxy.snmpConnInfo = device.getSnmpConnInfo()
        if manage_ip is not None and manage_ip != device.manageIp:
            proxy._config_id = device.id + "_" + manage_ip
            proxy.snmpConnInfo.manageIp = manage_ip
        # framework expects a value for this attr but snmp task uses
        # cycleInterval defined below
        proxy.configCycleInterval = getattr(
            device, "zSnmpCollectionInterval", 300
        )
        # this is the attr zenperfsnmp actually uses
        proxy.cycleInterval = proxy.configCycleInterval

        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.lastChangeTime = float(device.getLastChange())

        # Gather the datapoints to retrieve
        perfServer = device.getPerformanceServer()
        proxy.oids = {}
        proxy.thresholds = []
        if not components_only:
            # First for the device....
            threshs = self._getComponentConfig(device, perfServer, proxy.oids)
            if threshs:
                proxy.thresholds.extend(threshs)
        # And now for its components
        for comp in components:
            threshs = self._getComponentConfig(comp, perfServer, proxy.oids)
            if threshs:
                proxy.thresholds.extend(threshs)

        if proxy.oids:
            return proxy


if __name__ == "__main__":
    from Products.ZenHub.ServiceTester import ServiceTester

    tester = ServiceTester(SnmpPerformanceConfig)

    def printer(proxy):
        for oid in sorted(proxy.oids):
            print(oid)

    tester.printDeviceProxy = printer
    tester.showDeviceInfo()
