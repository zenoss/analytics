##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging

from Products.DataCollector.plugins.zenoss.snmp.HRFileSystemMap import (
    HRFileSystemMap,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class FakeDevice:
    def __init__(self, id):
        self.id = id


def dumpRelMap(relmap):
    """
    Display the contents returned from a modeler
    """
    for om in relmap:
        dumpObjectMapData(om)


def dumpObjectMapData(om):
    """
    I'm sure that 'Om' is not a reference to Terry Pratchet and
    the god of the same name.  Really.
    Anyway, this is a chance to view the mind of a small god.... :)
    """
    for attr in dir(om):
        obj = getattr(om, attr)
        if not attr.startswith("_") and not hasattr(obj, "__call__"):
            print("%s = %s" % (attr, obj))


class TestHRFileSystemMap(BaseTestCase):
    def afterSetUp(self):
        super(TestHRFileSystemMap, self).afterSetUp()

        self.fsmap = HRFileSystemMap()
        self.device = FakeDevice("testdevice")

    def checkfilesystems(self, obj):
        pass

    def testGoodResults(self):
        tabledata = {
            "fsTableOid": {
                "1": {
                    "blockSize": 1024,
                    "mount": "Memory Buffers",
                    "type": ".1.3.6.1.2.1.25.2.1.1",
                    "snmpindex": 1,
                    "totalBlocks": 1035292,
                },
                "3": {
                    "blockSize": 1024,
                    "mount": "Swap Space",
                    "type": ".1.3.6.1.2.1.25.2.1.3",
                    "snmpindex": 3,
                    "totalBlocks": 2031608,
                },
                "2": {
                    "blockSize": 1024,
                    "mount": "Real Memory",
                    "type": ".1.3.6.1.2.1.25.2.1.2",
                    "snmpindex": 2,
                    "totalBlocks": 1035292,
                },
                "5": {
                    "blockSize": 4096,
                    "mount": "/sys",
                    "type": ".1.3.6.1.2.1.25.2.1.4",
                    "snmpindex": 5,
                    "totalBlocks": 0,
                },
                "4": {
                    "blockSize": 4096,
                    "mount": "/",
                    "type": ".1.3.6.1.2.1.25.2.1.4",
                    "snmpindex": 4,
                    "totalBlocks": 999856,
                },
                "7": {
                    "blockSize": 4096,
                    "mount": "/proc/sys/fs/binfmt_misc",
                    "type": ".1.3.6.1.2.1.25.2.1.4",
                    "snmpindex": 7,
                    "totalBlocks": 0,
                },
                "6": {
                    "blockSize": 1024,
                    "mount": "/boot",
                    "type": ".1.3.6.1.2.1.25.2.1.4",
                    "snmpindex": 6,
                    "totalBlocks": 101086,
                },
                "8": {
                    "blockSize": 4096,
                    "mount": "/var/lib/nfs/rpc_pipefs",
                    "type": ".1.3.6.1.2.1.25.2.1.4",
                    "snmpindex": 8,
                    "totalBlocks": 0,
                },
            }
        }

        results = ("ignored", tabledata)
        relmap = HRFileSystemMap().process(self.device, results, log)
        parsed_data = {
            "totalSwap": {"compname": "os", "totalSwap": 2080366592},
            "totalMemory": {
                "compname": "hw",
                "totalMemory": 1060139008,
            },
            "maps": {"compname": "os", "relname": "filesystems"},
        }

        fs_data = {
            "Memory Buffers": {
                "blockSize": 1024,
                "compname": "os",
                "modname": "Products.ZenModel.FileSystem",
                "mount": "Memory Buffers",
                "snmpindex": 1,
                "totalBlocks": 1035292,
                "type": "other",
            },
            "Swap Space": {
                "blockSize": 1024,
                "compname": "os",
                "modname": "Products.ZenModel.FileSystem",
                "mount": "Swap Space",
                "snmpindex": 3,
                "totalBlocks": 2031608,
                "type": "virtualMemory",
            },
            "Real Memory": {
                "blockSize": 1024,
                "compname": "os",
                "modname": "Products.ZenModel.FileSystem",
                "mount": "Real Memory",
                "snmpindex": 2,
                "totalBlocks": 1035292,
                "type": "ram",
            },
            "-": {
                "blockSize": 4096,
                "compname": "os",
                "modname": "Products.ZenModel.FileSystem",
                "mount": "/",
                "snmpindex": 4,
                "totalBlocks": 999856,
                "type": "fixedDisk",
            },
            "boot": {
                "blockSize": 1024,
                "compname": "os",
                "modname": "Products.ZenModel.FileSystem",
                "mount": "/boot",
                "snmpindex": 6,
                "totalBlocks": 101086,
                "type": "fixedDisk",
            },
        }

        keyvals = parsed_data.keys()
        for om in relmap:
            for index in keyvals:
                if hasattr(om, index):
                    break
            else:
                self.fail(
                    "None of the keys %s were found in the return", keyvals
                )

            for attr in parsed_data[index].keys():
                self.assertEquals(getattr(om, attr), parsed_data[index][attr])

            if index == "maps":
                for fs_obj in om.maps:
                    fs_index = fs_obj.id
                    self.assert_(fs_index in fs_data)
                    for attr in fs_data[fs_index].keys():
                        self.assertEquals(
                            getattr(fs_obj, attr), fs_data[fs_index][attr]
                        )

                    del fs_data[fs_index]

            # We should only see the keys once
            del parsed_data[index]

        self.assertEquals(len(parsed_data), 0)
        self.assertEquals(len(fs_data), 0)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestHRFileSystemMap))
    return suite
