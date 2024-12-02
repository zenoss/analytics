##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class df(CommandPlugin):
    """
    Run df -k to model filesystem information. Should work on most *nix.
    """

    maptype = "FilesystemMap"
    command = "/bin/df -Pk"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"
    deviceProperties = CommandPlugin.deviceProperties + (
        "zFileSystemMapIgnoreNames",
    )

    oses = ["Linux", "Darwin", "SunOS", "AIX"]

    def condition(self, device, log):
        return device.os.uname == "" or device.os.uname in self.oses

    def process(self, device, results, log):
        log.info("Collecting filesystems for device %s", device.id)
        skipfsnames = getattr(device, "zFileSystemMapIgnoreNames", None)
        rm = self.relMap()
        rlines = results.split("\n")
        bline = ""
        for line in rlines:
            if line.startswith("Filesystem"):
                continue
            om = self.objectMap()
            spline = line.split()
            if len(spline) == 1:
                bline = spline[0]
                continue
            if bline:
                spline.insert(0, bline)
                bline = None
            if len(spline) != 6:
                continue
            (om.storageDevice, tblocks, u, a, p, om.mount) = spline
            if skipfsnames and re.search(skipfsnames, om.mount):
                continue

            if tblocks == "-":
                om.totalBlocks = 0
            else:
                try:
                    om.totalBlocks = long(tblocks)
                except ValueError:
                    # Ignore this filesystem if what we thought was total
                    # blocks isn't a number.
                    continue

            om.blockSize = 1024
            om.id = self.prepId(om.mount)
            om.title = om.mount
            rm.append(om)
        return rm
