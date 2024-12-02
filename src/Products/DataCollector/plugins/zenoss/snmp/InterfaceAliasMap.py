##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import GetTableMap
from Products.DataCollector.plugins.zenoss.snmp.InterfaceMap import (
    InterfaceMap,
)


class InterfaceAliasMap(InterfaceMap):
    """
    Extends the standard InterfaceMap to use the ifAlias as the interface's
    name instead of the ifDescr. This can be useful when many interfaces on
    the same device have the same ifDescr.
    """

    snmpGetTableMaps = InterfaceMap.baseSnmpGetTableMaps + (
        # Extended interface information.
        GetTableMap(
            "ifalias",
            ".1.3.6.1.2.1.31.1.1.1",
            {
                ".1": "ifName",
                ".6": "ifHCInOctets",
                ".7": "ifHCInUcastPkts",
                ".15": "highSpeed",
                ".18": "description",
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        # save proxy to self as superclass, to guard against future
        # reload of plugin module changing imported classes (making
        # future super calls fail due to class mismatch)
        self.as_super = super(InterfaceAliasMap, self)
        self.as_super.__init__(*args, **kwargs)

    def process(self, device, results, log):
        """
        Pre-process the IF-MIB ifXTable to use the ifAlias as the interface's
        name instead of the ifDescr.
        """
        if "ifalias" in results[1] and "iftable" in results[1]:
            for a_idx, alias in results[1]["ifalias"].items():
                for i_idx, iface in results[1]["iftable"].items():
                    if a_idx == i_idx:
                        results[1]["iftable"][i_idx]["id"] = alias["ifName"]

        return self.as_super.process(device, results, log)
