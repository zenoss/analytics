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


class InformantHardDiskMap(SnmpPlugin):
    """Map SNMP Informat sub-agent to HardDisk"""

    maptype = "HardDiskMap"
    modname = "Products.ZenModel.HardDisk"
    relname = "harddisks"
    compname = "hw"
    weight = 3

    snmpGetTableMaps = (
        GetTableMap(
            "logicalDiskEntry",
            ".1.3.6.1.4.1.9600.1.1.1.1",
            {
                ".1": "id",
            },
        ),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        dtable = tabledata.get("logicalDiskEntry")
        if not dtable:
            return
        rm = self.relMap()
        for oid, disk in dtable.items():
            om = self.objectMap(disk)
            if not om.id:
                continue
            if om.id == "_Total":
                continue
            om.description = om.id
            om.id = self.prepId(om.id)
            om.snmpindex = oid.lstrip(".")
            rm.append(om)
        return rm
