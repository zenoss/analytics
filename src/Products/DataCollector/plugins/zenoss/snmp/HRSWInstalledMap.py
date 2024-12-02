##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import (
    SnmpPlugin,
    GetTableMap,
)


class HRSWInstalledMap(SnmpPlugin):
    """Finds various software packages installed on a device.

    Uses the HOST-RESOURCES-MIB OIDs.
    """

    maptype = "SoftwareMap"
    modname = "Products.ZenModel.Software"
    relname = "software"
    compname = "os"

    columns = {
        ".1": "snmpindex",
        ".2": "setProductKey",
        # '.4': 'type',
        ".5": "setInstallDate",
    }
    snmpGetTableMaps = (
        GetTableMap("swTableOid", ".1.3.6.1.2.1.25.6.3.1", columns),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        swtable = tabledata.get("swTableOid")
        rm = self.relMap()
        for sw in swtable.values():
            om = self.objectMap(sw)
            om.id = self.prepId(om.setProductKey)
            if not om.id:
                continue
            if hasattr(om, "setInstallDate"):
                om.setInstallDate = self.asdate(om.setInstallDate)
            rm.append(om)
        return rm
