##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap

MULTIPLIERS = {"M": 1024 * 1024, "K": 1024, "B": 1}


class swap(CommandPlugin):
    """
    Reads from sysctl vm.swapusage and puts the swap total into the swap field.
    """

    maptype = "FileSystemMap"
    command = "/usr/sbin/sysctl vm.swapusage"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"

    def condition(self, device, log):
        return device.os.uname == "Darwin"

    def process(self, device, results, log):
        log.info("Collecting swap for device %s", device.id)

        self.relMap()
        maps = []

        results = results.split()
        total = results[3]
        multiplier = MULTIPLIERS[total[-1]]

        total = float(total[:-1]) * multiplier
        maps.append(ObjectMap({"totalSwap": total}, compname="os"))

        return maps
