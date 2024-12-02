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


class memory(CommandPlugin):
    """Maps sysclt hw.physmem output to the memory fields."""

    maptype = "FileSystemMap"
    command = "/usr/sbin/sysctl hw.physmem"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"

    def condition(self, device, log):
        return device.os.uname == "Darwin"

    def process(self, device, results, log):
        log.info("Collecting memory for device %s", device.id)

        self.relMap()
        maps = []

        results = results.split(":")[1].strip()
        totalMemory = int(results)
        maps.append(ObjectMap({"totalMemory": totalMemory}, compname="hw"))

        return maps
