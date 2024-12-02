##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class uname(CommandPlugin):
    """
    Determine the Operating System's name from the result of the
    uname command.
    """

    maptype = "DeviceMap"
    compname = "os"
    command = "uname"

    def process(self, device, results, log):
        """Collect command-line information from this device"""
        log.info("Processing the OS uname info for device %s", device.id)
        om = self.objectMap()
        om.uname = results.strip()
        log.debug("uname = %s", om.uname)
        return om
