##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin


class SysedgeDiskMap(SnmpPlugin):
    """Empire SysEDGE disk information."""

    remoteClass = "Products.ZenModel.HardDisk"
    relationshipName = "harddisks"
    componentName = "hw"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "zSysedgeDiskMapIgnoreNames",
    )

    hrDeviceDescr = ".1.3.6.1.2.1.25.3.2.1.3"
    diskStatsTable = ".1.3.6.1.4.1.546.12.1.1"
    diskMap = {
        ".1": "snmpindex",
        ".9": "hostresindex",
    }

    def condition(self, device, log):
        """Does device meet the proper conditions for this collector to run"""
        return False

    def collect(self, device, snmpsess, log):
        """Collect snmp information from this device"""
        log.info("Collecting disks for device %s", device.id)
        disktable = snmpsess.collectSnmpTableMap(
            self.diskStatsTable, self.diskMap
        )
        datamaps = []
        for diskrow in disktable.values():
            descoid = self.hrDeviceDescr + "." + str(diskrow["hostresindex"])
            desc = snmpsess.get(descoid)
            if len(desc) == 1:
                desc = desc.values()[0]
                diskrow["description"] = desc
                disknamereg = getattr(
                    device, "zSysedgeDiskMapIgnoreNames", None
                )
                if disknamereg and re.search(disknamereg, desc):
                    continue
                id = re.split(r"[,\s]", desc)[0]
                diskrow["title"] = id
                diskrow["id"] = self.prepId(id)
                datamaps.append(diskrow)
        return datamaps
