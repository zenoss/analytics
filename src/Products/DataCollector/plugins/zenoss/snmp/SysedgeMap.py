##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin


class SysedgeMap(SnmpPlugin):
    """Gather Empire SysEDGE disk OS and licensing information."""

    sysedgeMap = {
        ".1.3.6.1.4.1.546.1.1.1.8.0": "snmpAgent",
        ".1.3.6.1.4.1.546.1.1.1.17.0": "sysedgeLicenseMode",
        ".1.3.6.1.2.1.25.6.3.1.2.1": "setOSProductKey",
    }

    def condition(self, device, log):
        """Does device meet the proper conditions for this collector to run"""
        return False

    def collect(self, device, snmpsess, log):
        """Collect snmp information from this device"""
        log.info("Collecting sysedge info for device %s", device.id)
        data = snmpsess.get(self.sysedgeMap.keys())
        retdata = {}
        for oid in data.keys():
            key = self.sysedgeMap[oid]
            retdata[key] = data[oid]
            if key == "snmpSysedgeMode":
                if data[oid] == 1:
                    retdata[key] = "fullMode"
                else:
                    retdata[key] = "restrictedMode"
        return retdata
