##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap


class DeviceMap(SnmpPlugin):
    """
    Gathers information (sysDescr, sysContact, sysName, and sysLocation)
    and adds it to the device.

    To obtain a better OS and hardware manufacturer mapping, use the
    NewDeviceMap modeler plugin.
    """

    maptype = "DeviceMap"

    columns = {
        ".1.3.6.1.2.1.1.1.0": "snmpDescr",
        ".1.3.6.1.2.1.1.2.0": "snmpOid",
        # '.1.3.6.1.2.1.1.3.0' : 'snmpUpTime',
        ".1.3.6.1.2.1.1.4.0": "snmpContact",
        ".1.3.6.1.2.1.1.5.0": "snmpSysName",
        ".1.3.6.1.2.1.1.6.0": "snmpLocation",
    }
    snmpGetMap = GetMap(columns)

    ciscoVersion = re.compile(r"Version (?P<ver>.+), ")

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        if not self.checkColumns(getdata, self.columns, log):
            return
        om = self.objectMap(getdata)

        # allow for custom parse of DeviceMap data
        scDeviceMapParse = getattr(device, "scDeviceMapParse", None)
        if scDeviceMapParse:
            om = scDeviceMapParse(device, om)

        return om
