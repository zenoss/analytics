##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class uname_a(CommandPlugin):
    """
    Determine snmpSysName and setOSProductKey from the result of the uname -a
    command.
    """

    maptype = "DeviceMap"
    compname = ""
    command = "uname -a"

    def process(self, device, results, log):
        """Collect command-line information from this device"""
        log.info("Processing the uname -a info for device %s", device.id)
        om = self.objectMap()
        om.snmpDescr = results.strip()
        om.setHWProductKey, om.snmpSysName, kernelRelease = results.split()[:3]
        om.setOSProductKey = " ".join([om.setHWProductKey, kernelRelease])
        log.debug(
            "snmpSysName=%s, setOSProductKey=%s",
            om.snmpSysName,
            om.setOSProductKey,
        )
        return om
