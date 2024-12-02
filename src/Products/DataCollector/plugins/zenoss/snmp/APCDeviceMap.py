##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap
from Products.DataCollector.plugins.DataMaps import MultiArgs


class APCDeviceMap(SnmpPlugin):
    """Gather information from APC UPS devices."""

    maptype = "APCDeviceMap"

    snmpGetMap = GetMap(
        {
            ".1.3.6.1.4.1.318.1.1.1.1.1.1.0": "setHWProductKey",
            ".1.3.6.1.4.1.318.1.1.1.1.2.3.0": "setHWSerialNumber",
        }
    )

    def condition(self, device, log):
        """only for boxes with proper object id"""
        return device.snmpOid.startswith(".1.3.6.1.4.1.318")

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        om.setHWProductKey = MultiArgs(om.setHWProductKey, "APC")
        return om
