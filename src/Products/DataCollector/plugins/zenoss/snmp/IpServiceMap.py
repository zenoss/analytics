##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)


class IpServiceMap(SnmpPlugin):
    """
    IpServiceMap maps the TCP/IP services running on a machine to
    IP Service objects.  Note that only TCP services can be monitored.
    """

    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = SnmpPlugin.deviceProperties + ("zIpServiceMapMaxPort",)

    snmpGetTableMaps = (
        GetTableMap("tcptable", ".1.3.6.1.2.1.6.13.1", {".1": "state"}),
        GetTableMap("udptable", ".1.3.6.1.2.1.7.5.1", {".1": "addr"}),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        tcptable = tabledata.get("tcptable", {})
        udptable = tabledata.get("udptable", {})
        rm = self.relMap()
        maxport = getattr(device, "zIpServiceMapMaxPort", 1024)
        # tcp services
        if tcptable:
            tcpports = {}
            for oid, value in tcptable.items():
                if value["state"] != 2:
                    continue
                oidar = oid.split(".")
                addr = ".".join(oidar[-10:-6])
                port = int(oidar[-6])
                if port > maxport or port < 1:
                    continue
                om = tcpports.get(port, None)
                if om:
                    om.ipaddresses.append(addr)
                else:
                    om = self.objectMap()
                    om.id = "tcp_%05d" % port
                    om.ipaddresses = [
                        addr,
                    ]
                    om.protocol = "tcp"
                    om.port = port
                    om.setServiceClass = {"protocol": "tcp", "port": port}
                    om.discoveryAgent = self.name()
                    tcpports[port] = om
                    rm.append(om)

        # udp services
        if udptable:
            udpports = {}
            for oid, value in udptable.items():
                oid = oid.split(".")
                port = int(oid[-1])
                if port > maxport or port < 1:
                    continue
                addr = value["addr"]
                om = udpports.get(port, None)
                if om:
                    om.ipaddresses.append(addr)
                else:
                    om = self.objectMap()
                    om.id = "udp_%05d" % port
                    om.ipaddresses = [
                        addr,
                    ]
                    om.protocol = "udp"
                    om.port = port
                    om.monitor = False
                    om.setServiceClass = {"protocol": "udp", "port": port}
                    om.discoveryAgent = self.name()
                    udpports[port] = om
                    rm.append(om)
        return rm
