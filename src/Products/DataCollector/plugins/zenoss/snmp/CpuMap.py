##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.DataCollector.plugins.DataMaps import MultiArgs


def getManufacturerAndModel(key):
    """
    Attempts to parse accurate manufacturer and model information of a CPU from
    the single product string passed in.

    @param key: A product key. Hopefully containing manufacturer and model
        name.
    @type key: string
    @return: A MultiArgs object containing the model and manufacturer.
    @rtype: Products.DataDollector.plugins.DataMaps.MultiArgs
    """
    cpuDict = {
        "Intel": "(Intel|Pentium|Xeon)",
        "AMD": "(AMD|Opteron|Athlon|Sempron|Phenom|Turion)",
    }

    for manufacturer, regex in cpuDict.items():
        if re.search(regex, key):
            return MultiArgs(key, manufacturer)

    # Revert to default behavior if no specific match is found.
    return MultiArgs(key, "Unknown")


class CpuMap(SnmpPlugin):
    """CpuMap maps SNMP cpu information onto CPUs."""

    maptype = "CPUMap"
    compname = "hw"
    relname = "cpus"
    modname = "Products.ZenModel.CPU"

    columns = {
        ".2": "_type",
        ".3": "_description",
    }

    snmpGetTableMaps = (
        GetTableMap("deviceTableOid", ".1.3.6.1.2.1.25.3.2.1", columns),
    )

    hrDeviceProcessor = ".1.3.6.1.2.1.25.3.1.3"

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        table = tabledata.get("deviceTableOid")
        rm = self.relMap()
        slot = 0
        for snmpindex, row in table.items():
            if not rm and not self.checkColumns(row, self.columns, log):
                return rm
            if row["_type"] != self.hrDeviceProcessor:
                continue
            desc = row["_description"]
            # try and find the cpu speed from the description
            match = re.search("([.0-9]+) *([mg]hz)", desc.lower())
            if match:
                try:
                    speed = float(match.group(1))
                    if match.group(2).startswith("g"):
                        speed *= 1000
                    row["clockspeed"] = int(speed)
                except ValueError:
                    pass
            om = self.objectMap(row)
            om.setProductKey = getManufacturerAndModel(desc)
            om.id = "%d" % slot
            om.snmpindex = snmpindex.strip(".")
            slot += 1
            rm.append(om)

        return rm
