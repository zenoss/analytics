##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.ZenUtils import IpUtil

log = logging.getLogger("zen.IpV6ServiceMap")


class IpV6ServiceMap(SnmpPlugin):
    """
    Creates IpV4 Services from IPV6 descriptions that allow
    all incoming requests (address ::).
    """

    PORT_MIN = 0x1
    PORT_MAX = 0xFFFF

    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = SnmpPlugin.deviceProperties + ("zIpServiceMapMaxPort",)

    snmpGetTableMaps = (
        GetTableMap(
            "tcplisten", ".1.3.6.1.2.1.6.20.1.4", {".1": "v4", ".2": "v6"}
        ),
        GetTableMap(
            "udpendpoint", ".1.3.6.1.2.1.7.7.1.8", {".1": "v4", ".2": "v6"}
        ),
    )

    def ignoredAddr(self, addr):
        # ignore localhost designations
        # 127.0.0.0/8
        # ::1
        return addr in ["::1"] or addr.startswith("127.")

    def _extractAddressAndPort(self, oid):
        try:
            oid_parts = oid.split(".")
            addr_type = int(oid_parts[0])
            port = int(oid_parts[-1])
            addr_parts = oid_parts[1:-1]
            result = []

            if len(addr_parts) != addr_type:
                log.debug("Invalid oid %s", oid)
                return []
            if not self.PORT_MIN <= port <= self.PORT_MAX:
                log.debug("Port value exceeds range for oid %s", oid)
                return []

            addr = IpUtil.bytesToCanonIp(addr_parts)
            if not self.ignoredAddr(addr):
                log.debug("Adding addr: %s", addr)
                result.append((addr, port))
            else:
                log.debug("Ignoring addr: %s", addr)

            # Any IPv6 address is inclusive of any IPv4 addresses as well
            if addr == IpUtil.IPV6_ANY_ADDRESS:
                result.append((IpUtil.IPV4_ANY_ADDRESS, port))
        except Exception as e:
            log.debug("Unable to process oid %s: %s", oid, e)
            return []

        return result

    def _getProtocolObjectMap(self, protocol, addr, port):
        om = self.objectMap()
        om.id = "%s_%05d" % (protocol, port)
        om.ipaddresses = [
            addr,
        ]
        om.protocol = protocol
        om.port = port
        om.setServiceClass = {"protocol": protocol, "port": port}
        om.discoveryAgent = self.name()
        return om

    def _processTcp(self, tcplisten):
        result = []
        for oid in tcplisten:
            for addr, port in self._extractAddressAndPort(oid):
                om = self._getProtocolObjectMap("tcp", addr, port)
                result.append(om)
        return result

    def _processUdp(self, udpendpoint):
        result = []
        for oid in udpendpoint:
            # UDP returns local + remote information, but we only need local
            # Format: local_addr_type.{ip address}.port.remote_addr_type.{ip address}.port  # noqa E501
            # Eg. 4.100.210.23.45.8080.4.235.45.56.4.2709
            oid_parts = oid.split(".")
            local_addr_type = int(oid_parts[0])
            local_oid_parts = oid_parts[: local_addr_type + 2]
            local_oid = ".".join(local_oid_parts)
            for addr, port in self._extractAddressAndPort(local_oid):
                om = self._getProtocolObjectMap("udp", addr, port)
                om.monitor = False
                result.append(om)
        return result

    def _reduceByPort(self, maxport, rm, maps):
        ports = {}
        for map in maps:
            addr = map.ipaddresses[0]
            port = map.port
            if port > maxport:
                continue
            om = ports.get(port, None)
            if om:
                if addr not in om.ipaddresses:
                    om.ipaddresses.append(addr)
            else:
                ports[port] = map
                rm.append(map)

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        tcplisten = tabledata.get("tcplisten")
        udpendpoint = tabledata.get("udpendpoint")
        if tcplisten is None or udpendpoint is None:
            return
        rm = self.relMap()
        maxport = getattr(device, "zIpServiceMapMaxPort", 1024)
        self._reduceByPort(maxport, rm, self._processTcp(tcplisten))
        self._reduceByPort(maxport, rm, self._processUdp(udpendpoint))
        return rm
