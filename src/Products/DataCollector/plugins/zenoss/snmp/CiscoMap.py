##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re
import sys

from Products.DataCollector.plugins.CollectorPlugin import (
    GetMap,
    GetTableMap,
    SnmpPlugin,
)
from Products.DataCollector.plugins.DataMaps import ObjectMap


class CiscoMap(SnmpPlugin):
    """
    Models Cisco device attributes.
        * Serial Number
        * Total Memory
    """

    maptype = "CiscoDeviceMap"

    snmpGetMap = GetMap(
        {
            ".1.3.6.1.2.1.1.2.0": "snmpOid",
            ".1.3.6.1.4.1.9.3.6.3.0": "_serialNumber",
            ".1.3.6.1.4.1.9.9.48.1.1.1.5.1": "_memUsed",
            ".1.3.6.1.4.1.9.9.48.1.1.1.6.1": "_memFree",
        }
    )

    snmpGetTableMaps = (
        GetTableMap(
            "entPhysicalTable", ".1.3.6.1.2.1.47.1.1.1.1", {".11": "serialNum"}
        ),
    )

    badSerialPatterns = [
        # Cisco, Catalyst, CAT
        r"^(Cisco|Catalyst|CAT)$",
        # 0x0E
        r"^0x",
        # WS-C3548-XL
        r"^WS-",
        # VG224
        r"^VG\d{3}$",
        # C3845-VSEC-SRST/K9
        r"^C\d{4}-",
        # Model numbers: 1841, 2811, 2851, 3845, etc.
        r"^\d{4}$",
        # Other
        r"^(CISCO|C|Cat|CAT|AS)?\d{4}[A-Z]{0,2}(-(\w|\d{0,3}))?$",
    ]

    snmpOidPreferEntity = [
        ".1.3.6.1.4.1.9.1.525",  # ciscoAIRAP1210
    ]

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info("processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results

        maps = []

        serialNumber = self.getSerialNumber(getdata, tabledata)
        if serialNumber is not None:
            maps.append(ObjectMap({"setHWSerialNumber": serialNumber}))

        totalMemory = self.getTotalMemory(getdata)
        if totalMemory is not None:
            maps.append(ObjectMap({"totalMemory": totalMemory}, compname="hw"))

        return maps

    def getSerialNumber(self, getdata, tabledata):
        serialNumber = getdata.get("_serialNumber", None)

        # In most cases we want to prefer the serial number in the Cisco
        # enterprise MIB if it is available.
        preferEntityMib = False
        if getdata.get("_snmpOid", None) in self.snmpOidPreferEntity:
            preferEntityMib = True

        if serialNumber and not preferEntityMib:

            # If there's a space in the serial we only want the first part.
            serialNumber = serialNumber.split(" ", 1)[0]

            # There are Cisco devices out there that return invalid serial
            # numbers with non-ASCII characters. Note them.
            try:
                _ = serialNumber.encode("ascii")
            except (UnicodeEncodeError, UnicodeDecodeError):
                serialNumber = "Invalid"

            # Some Cisco devices return a bogus serial. Ignore them.
            for pattern in self.badSerialPatterns:
                if re.match(pattern, serialNumber):
                    break
            else:
                return serialNumber

        # Some Cisco devices expose their serial number via the ENTITY-MIB.
        entPhysicalTable = tabledata.get("entPhysicalTable", {})

        lowestIndex = sys.maxint
        for index, entry in entPhysicalTable.items():
            serialNum = entry.get("serialNum", None)
            if serialNum and int(index) < lowestIndex:
                serialNumber = serialNum
                lowestIndex = int(index)

        # Return the serial number if we found one. Otherwise don't overwrite
        # a value provided by another modeler plugin.
        return serialNumber

    def getTotalMemory(self, getdata):
        used = getdata.get("_memUsed", None)
        free = getdata.get("_memFree", None)
        if used is not None and free is not None:
            return used + free

        return None
