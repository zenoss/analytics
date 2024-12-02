##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin
from Products.DataCollector.plugins.DataMaps import ObjectMap

MULTIPLIER = {"kB": 1024, "MB": 1024 * 1024, "b": 1}


class memory(LinuxCommandPlugin):
    """Maps /proc/meminfo to the memory and swap fields."""

    maptype = "FileSystemMap"
    command = "cat /proc/meminfo"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"

    def process(self, device, results, log):
        log.info("Collecting memory and swap for device %s", device.id)

        self.relMap()
        maps = []

        for line in results.split("\n"):
            vals = line.split(":")
            if len(vals) != 2:
                continue

            name, value = vals
            vals = value.split()
            if len(vals) != 2:
                continue

            value, unit = vals
            size = int(value) * MULTIPLIER.get(unit, 1)

            if name == "MemTotal":
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            if name == "SwapTotal":
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))

        return maps
