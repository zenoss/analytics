##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.ZenUtils.Utils import unsigned


class HRFileSystemMap(SnmpPlugin):
    """Maps the filesystems to filesystem objects."""

    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "zFileSystemMapIgnoreNames",
        "zFileSystemMapIgnoreTypes",
    )

    columns = {
        ".1": "snmpindex",
        ".2": "type",
        ".3": "mount",
        ".4": "blockSize",
        ".5": "totalBlocks",
    }

    dskTableOid = "1.3.6.1.4.1.2021.9.1"
    dskTableColumns = {
        ".1": "dskIndex",
        ".2": "dskPath",
    }

    snmpGetTableMaps = (
        GetTableMap("fsTableOid", ".1.3.6.1.2.1.25.2.3.1", columns),
        GetTableMap("dskTable", dskTableOid, dskTableColumns),
        GetTableMap(
            "hrFSEntry",
            ".1.3.6.1.2.1.25.3.8.1",
            {".2": "mount", ".7": "storageIndex"},
        ),
    )

    typemap = {
        ".1.3.6.1.2.1.25.2.1.1": "other",
        ".1.3.6.1.2.1.25.2.1.2": "ram",
        ".1.3.6.1.2.1.25.2.1.3": "virtualMemory",
        ".1.3.6.1.2.1.25.2.1.4": "fixedDisk",
        ".1.3.6.1.2.1.25.2.1.5": "removableDisk",
        ".1.3.6.1.2.1.25.2.1.6": "floppyDisk",
        ".1.3.6.1.2.1.25.2.1.7": "compactDisk",
        ".1.3.6.1.2.1.25.2.1.8": "ramDisk",
        ".1.3.6.1.2.1.25.2.1.9": "flashMemory",
        ".1.3.6.1.2.1.25.2.1.10": "networkDisk",
    }

    def process(self, device, results, log):
        """Process SNMP information from this device"""
        log.info(
            "Modeler %s processing data for device %s", self.name(), device.id
        )
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)
        fstable = tabledata.get("fsTableOid")
        if fstable is None:
            log.error(
                "Unable to get data for %s from fsTableOid"
                " -- skipping model",
                device.id,
            )
            return None

        dskTable = tabledata.get("dskTable")

        hrFSEntry = tabledata.get("hrFSEntry", {})
        remoteMountMap = self._createRemoteMountMap(hrFSEntry)

        skipfsnames = getattr(device, "zFileSystemMapIgnoreNames", None)
        skipfstypes = getattr(device, "zFileSystemMapIgnoreTypes", None)
        maps = []
        rm = self.relMap()
        for fs in fstable.values():
            if not self.checkColumns(fs, self.columns, log):
                continue

            # Gentoo and openSUSE report "Virtual memory" as swap. This needs
            # to be ignored so we can pickup the real swap later in the table.
            if "virtual memory" in fs["mount"].lower():
                continue

            rmount = remoteMountMap.get(fs["snmpindex"])
            if rmount is not None and fs["mount"] != rmount:
                log.debug("Switching mount from %s to %s", fs["mount"], rmount)
                fs["storageDevice"] = rmount

            totalBlocks = fs["totalBlocks"]

            # Large file systems can report as an unsigned integer
            if totalBlocks < 0:
                totalBlocks = unsigned(totalBlocks)
                fs["totalBlocks"] = totalBlocks

            size = long(fs["blockSize"] * totalBlocks)
            if size <= 0:
                log.info("Skipping %s. 0 total blocks.", fs["mount"])
                continue

            fs["type"] = self.typemap.get(fs["type"], "other")
            size = long(fs["blockSize"] * totalBlocks)

            # Handle file systems that need to be mapped into other parts of
            # the model such as total memory or total swap.
            if fs["type"] == "ram":
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            elif fs["type"] == "virtualMemory" or fs["mount"] == "Swap":
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))

            if skipfsnames and re.search(skipfsnames, fs["mount"]):
                log.info(
                    "Skipping %s as it matches zFileSystemMapIgnoreNames.",
                    fs["mount"],
                )
                continue

            if skipfstypes and fs["type"] in skipfstypes:
                log.info(
                    "Skipping %s (%s) as it matches "
                    "zFileSystemMapIgnoreTypes.",
                    fs["mount"],
                    fs["type"],
                )
                continue

            fs["snmpindex_dct"] = {
                HRFileSystemMap.dskTableOid: self._getDskIndex(
                    dskTable, fs["mount"]
                )
            }

            om = self.objectMap(fs)
            om.id = self.prepId(om.mount)
            om.title = om.mount
            rm.append(om)
        maps.append(rm)

        # look for any map 'm' with m.compname == 'os' and m.totalSwap > 0
        if not any(
            getattr(m, "compname", None) == "os"
            and getattr(m, "totalSwap", 0) > 0
            for m in maps
        ):
            # if no value set for device.os.totalSwap, set totalSwap to 0
            log.info(
                "Swap space not detected for device %s, setting to 0",
                device.id,
            )
            maps.append(ObjectMap({"totalSwap": 0}, compname="os"))

        return maps

    def _getDskIndex(self, dskTable, dskPath):
        retval = None
        if dskTable is not None:
            for dsk in dskTable.values():
                if dsk.get("dskPath") == dskPath:
                    retval = dsk.get("dskIndex")
                    break
        return retval

    def _createRemoteMountMap(self, table):
        mountMap = {}
        duplicateIndexes = set()
        for data in table.values():
            sindex = data["storageIndex"]
            if sindex in mountMap:
                duplicateIndexes.add(sindex)
                continue
            mountMap[sindex] = data["mount"]

        for index in duplicateIndexes:
            del mountMap[index]
        return mountMap
