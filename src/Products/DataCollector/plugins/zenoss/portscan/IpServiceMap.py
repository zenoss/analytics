##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import CollectorPlugin


class IpServiceMap(CollectorPlugin):
    """Maps the interface and ip tables to interface objects."""

    transport = "portscan"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = CollectorPlugin.deviceProperties + (
        "zIpServiceMapMaxPort",
    )

    def condition(self, device, log):
        """
        Default condition for portscan is True.
        """
        return True

    def preprocess(self, results, log):
        """
        Make sure the ports are integers.
        """
        addr = results.keys()[0]
        ports = [int(port) for port in results[addr]]
        return (addr, ports)

    def process(self, device, results, log):
        """
        Collect open port information from this device.
        """
        log.info("processing Ip Services for device %s", device.id)
        addr, ports = results
        rm = self.relMap()
        for port in ports:
            om = self.objectMap()
            om.id = "tcp_%05d" % port
            om.ipaddresses = [addr]
            om.protocol = "tcp"
            om.port = port
            om.setServiceClass = {"protocol": "tcp", "port": port}
            om.discoveryAgent = self.name()
            rm.append(om)
        return rm
