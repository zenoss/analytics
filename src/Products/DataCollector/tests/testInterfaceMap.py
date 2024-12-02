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

from Products.DataCollector.plugins.zenoss.snmp.InterfaceMap import (
    InterfaceMap,
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


class TestInterfaceMap(BaseTestCase):
    def afterSetUp(self):
        super(TestInterfaceMap, self).afterSetUp()

        self.imap = InterfaceMap()
        self.device = FakeDevice("testdevice")

    def testGoodResults(self):
        tabledata = {
            "ifalias": {
                "1": {"highSpeed": 0, "description": ""},
                "3": {"highSpeed": 0, "description": ""},
                "5": {"highSpeed": 0, "description": ""},
            },
            "iftable": {
                "1": {
                    "adminStatus": 1,
                    "macaddress": "",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 16436,
                    "ifindex": 1,
                    "type": 24,
                    "id": "lo",
                },
                "3": {
                    "adminStatus": 2,
                    "macaddress": "",
                    "operStatus": 2,
                    "speed": 0,
                    "mtu": 1480,
                    "ifindex": 3,
                    "type": 131,
                    "id": "sit0",
                },
                "5": {
                    "adminStatus": 1,
                    "macaddress": "\x00\x0c\x8d\xfd\x22\xd3",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 1500,
                    "ifindex": 5,
                    "type": 6,
                    "id": "eth0",
                },
            },
            "ipAddrTable": {
                "10.175.211.118": {
                    "ifindex": 5,
                    "netmask": "255.255.255.0",
                    "ipAddress": "10.175.211.118",
                },
                "127.0.0.1": {
                    "ifindex": 1,
                    "netmask": "255.0.0.0",
                    "ipAddress": "127.0.0.1",
                },
            },
            "ipNetToMediaTable": {
                "5.10.175.211.117": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.117",
                    "iptype": 3,
                },
                "5.10.175.211.116": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.116",
                    "iptype": 3,
                },
                "5.10.175.211.115": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.115",
                    "iptype": 3,
                },
                "5.10.175.211.121": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.121",
                    "iptype": 3,
                },
                "5.10.175.211.179": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.179",
                    "iptype": 3,
                },
                "5.10.175.211.34": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.34",
                    "iptype": 3,
                },
                "5.10.175.211.1": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.1",
                    "iptype": 3,
                },
                "5.10.175.211.10": {
                    "ifindex": 5,
                    "ipaddress": "10.175.211.10",
                    "iptype": 3,
                },
            },
        }

        results = ("ignored", tabledata)
        relmap = InterfaceMap().process(self.device, results, log)
        parsed_data = {
            5: {
                "id": "eth0",
                "macaddress": "00:0C:8D:FD:22:D3",
                "speed": 10000000,
                "mtu": 1500,
                "interfaceName": "eth0",
                "type": "ethernetCsmacd",
                "setIpAddresses": ["10.175.211.118/24"],
            },
            1: {
                "id": "lo",
                "speed": 10000000,
                "mtu": 16436,
                "interfaceName": "lo",
                "type": "softwareLoopback",
            },
            3: {
                "id": "sit0",
                "speed": 0,
                "mtu": 1480,
                "interfaceName": "sit0",
                "type": "Encapsulation Interface",
            },
        }

        for om in relmap:
            index = om.ifindex
            for attr in parsed_data[index].keys():
                self.assertEquals(getattr(om, attr), parsed_data[index][attr])

    def testNon24Netmask(self):
        tabledata = {
            "ifalias": {
                "1": {"highSpeed": 0, "description": ""},
                "3": {"highSpeed": 0, "description": ""},
                "2": {"highSpeed": 0, "description": ""},
            },
            "iftable": {
                "1": {
                    "adminStatus": 1,
                    "macaddress": "",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 16436,
                    "ifindex": 1,
                    "type": 24,
                    "id": "lo",
                },
                "3": {
                    "adminStatus": 2,
                    "macaddress": "",
                    "operStatus": 2,
                    "speed": 0,
                    "mtu": 1480,
                    "ifindex": 3,
                    "type": 131,
                    "id": "sit0",
                },
                "2": {
                    "adminStatus": 1,
                    "macaddress": "\x00\x0c\x8d\xfd\x22\xd3",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 1500,
                    "ifindex": 2,
                    "type": 6,
                    "id": "eth0",
                },
                "4": {
                    "adminStatus": 1,
                    "macaddress": "",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 16436,
                    "ifindex": 4,
                    "type": 6,
                    "id": "vlan1",
                },
                "5": {
                    "adminStatus": 1,
                    "macaddress": "",
                    "operStatus": 1,
                    "speed": 10000000,
                    "mtu": 16436,
                    "ifindex": 5,
                    "type": 6,
                    "id": "vlan2",
                },
            },
            "ipAddrTable": {
                "10.1.254.8": {
                    "ifindex": 2,
                    "netmask": "255.255.128.0",
                    "ipAddress": "10.1.254.8",
                },
                "127.0.0.1": {
                    "ifindex": 1,
                    "netmask": "255.0.0.0",
                    "ipAddress": "127.0.0.1",
                },
                "119.120.121.170.1": {
                    "ifindex": 4,
                    "netmask": "255.255.255.248",
                    "ipAddress": "119.120.121.170",
                },
                "122.123.124.170.1": {
                    "ifindex": 5,
                    "netmask": "255.255.255.248",
                },
            },
            "ipNetToMediaTable": {
                "2.10.1.254.107": {
                    "ifindex": 2,
                    "ipaddress": "10.1.254.107",
                    "iptype": 3,
                },
                "2.10.1.254.254": {
                    "ifindex": 2,
                    "ipaddress": "10.1.254.254",
                    "iptype": 3,
                },
                "2.10.1.252.54": {
                    "ifindex": 2,
                    "ipaddress": "10.1.252.54",
                    "iptype": 3,
                },
                "2.10.1.246.11": {
                    "ifindex": 2,
                    "ipaddress": "10.1.246.11",
                    "iptype": 3,
                },
                "2.10.1.254.61": {
                    "ifindex": 2,
                    "ipaddress": "10.1.254.61",
                    "iptype": 3,
                },
                "2.10.1.254.170": {
                    "ifindex": 2,
                    "ipaddress": "10.1.254.170",
                    "iptype": 3,
                },
            },
        }

        results = ("ignored", tabledata)
        relmap = InterfaceMap().process(self.device, results, log)

        parsed_data = {
            2: {
                "id": "eth0",
                "macaddress": "00:0C:8D:FD:22:D3",
                "speed": 10000000,
                "mtu": 1500,
                "interfaceName": "eth0",
                "type": "ethernetCsmacd",
            },
            "setIpAddresses": ["10.1.254.8/17"],
            1: {
                "id": "lo",
                "speed": 10000000,
                "mtu": 16436,
                "interfaceName": "lo",
                "setIpAddresses": ["127.0.0.1/8"],
                "type": "softwareLoopback",
            },
            3: {
                "id": "sit0",
                "speed": 0,
                "mtu": 1480,
                "interfaceName": "sit0",
                "type": "Encapsulation Interface",
            },
            4: {
                "id": "vlan1",
                "speed": 10000000,
                "mtu": 16436,
                "interfaceName": "vlan1",
                "setIpAddresses": ["119.120.121.170/29"],
                "type": "ethernetCsmacd",
            },
            5: {
                "id": "vlan2",
                "speed": 10000000,
                "mtu": 16436,
                "interfaceName": "vlan2",
                "setIpAddresses": ["122.123.124.170/29"],
                "type": "ethernetCsmacd",
            },
        }

        for om in relmap:
            index = om.ifindex
            for attr in parsed_data[index].keys():
                self.assertEquals(getattr(om, attr), parsed_data[index][attr])

    def testNoIpInterfaces(self):
        tabledata = {
            "ifalias": {
                "1": {
                    "highSpeed": 2000,
                    "description": "",
                    "ifHCInUcastPkts": 483106528092,
                    "ifHCInOctets": 123411643670667,
                },
                "2": {
                    "highSpeed": 0,
                    "description": "",
                    "ifHCInUcastPkts": 9531554,
                    "ifHCInOctets": 1211994446,
                },
                "3": {
                    "highSpeed": 2000,
                    "description": "",
                    "ifHCInUcastPkts": 506823808298,
                    "ifHCInOctets": 561671987287258,
                },
                "4": {
                    "highSpeed": 1000,
                    "description": "",
                    "ifHCInUcastPkts": 253321260579,
                    "ifHCInOctets": 280765628338066,
                },
            },
            "iftable": {
                "1": {
                    "adminStatus": 1,
                    "macaddress": "\x02\xd0h\x18U\xe1",
                    "operStatus": 1,
                    "speed": 2000000000,
                    "mtu": 1500,
                    "ifindex": 1,
                    "type": 6,
                    "id": "LA/1",
                },
                "2": {
                    "adminStatus": 1,
                    "macaddress": "\x00\xd0h\x18U\xdf",
                    "operStatus": 1,
                    "speed": 0,
                    "mtu": 1500,
                    "ifindex": 2,
                    "type": 6,
                    "id": "LO/1",
                },
                "3": {
                    "adminStatus": 1,
                    "macaddress": "\x02\xd0h\x18U\xe2",
                    "operStatus": 1,
                    "speed": 2000000000,
                    "mtu": 1500,
                    "ifindex": 3,
                    "type": 6,
                    "id": "LA/2",
                },
                "4": {
                    "adminStatus": 1,
                    "macaddress": "\x00\xd0h\x18U\xe1",
                    "operStatus": 1,
                    "speed": 1000000000,
                    "mtu": 1500,
                    "ifindex": 4,
                    "type": 6,
                    "id": "1/3",
                },
            },
            "ipAddrTable": {},
            "ipNetToMediaTable": {},
        }
        results = ("ignored", tabledata)
        relmap = InterfaceMap().process(self.device, results, log)

        parsed_data = {
            1: {
                "id": "LA_1",
                "interfaceName": "LA/1",
                "title": "LA/1",
                "type": "ethernetCsmacd_64",
                "macaddress": "02:D0:68:18:55:E1",
                "setIpAddresses": [],
                "speed": 2000000000,
                "mtu": 1500,
            },
            2: {
                "id": "LO_1",
                "interfaceName": "LO/1",
                "title": "LO/1",
                "type": "ethernetCsmacd_64",
                "macaddress": "00:D0:68:18:55:DF",
                "setIpAddresses": [],
                "speed": 0,
                "mtu": 1500,
            },
            3: {
                "id": "LA_2",
                "interfaceName": "LA/2",
                "title": "LA/2",
                "type": "ethernetCsmacd_64",
                "macaddress": "02:D0:68:18:55:E2",
                "setIpAddresses": [],
                "speed": 2000000000,
                "mtu": 1500,
            },
            4: {
                "id": "1_3",
                "interfaceName": "1/3",
                "title": "1/3",
                "type": "ethernetCsmacd_64",
                "macaddress": "00:D0:68:18:55:E1",
                "setIpAddresses": [],
                "speed": 1000000000,
                "mtu": 1500,
            },
        }

        for om in relmap:
            index = om.ifindex
            for attr in parsed_data[index].keys():
                self.assertEquals(getattr(om, attr), parsed_data[index][attr])


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestInterfaceMap))
    return suite
