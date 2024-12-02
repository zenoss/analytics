##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from cPickle import loads

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.CpuMap import (
    CpuMap,
    getManufacturerAndModel,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class TestCpuMap(BaseTestCase):
    def afterSetUp(self):
        super(TestCpuMap, self).afterSetUp()
        self.adm = ApplyDataMap()
        self.cmap = CpuMap()
        self.device = self.dmd.Devices.createInstance("testDevice")

    def testWin2003Server(self):
        results = loads(
            "((dp1\n(dp2\nS'deviceTableOid'\np3\n(dp4\nS'11'\np5\n"
            "(dp6\nS'_type'\np7\nS'.1.3.6.1.2.1.25.3.1.4'\np8\n"
            "sS'_description'\np9\nS'Broadcom NetXtreme Gigabit Ethernet "
            "- SecuRemote Miniport'\np10\nssS'10'\np11\n(dp12\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.4'\np13\nsg9\nS'Broadcom NetXtreme "
            "Gigabit Ethernet #2 - SecuRemote Miniport'\np14\nssS'13'\n"
            "p15\n(dp16\ng7\nS'.1.3.6.1.2.1.25.3.1.6'\np17\nsg9\n"
            "S'Fixed Disk'\np18\nssS'12'\np19\n(dp20\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.6'\np21\nsg9\nS'D:\\\\'\np22\nssS'15'\n"
            "p23\n(dp24\ng7\nS'.1.3.6.1.2.1.25.3.1.16'\np25\nsg9\n"
            "S'5-Buttons  (with wheel)'\np26\nssS'14'\np27\n(dp28\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.13'\np29\nsg9\nS'IBM enhanced (101- or "
            "102-key) keyboard, Subtype=(0)'\np30\nssS'16'\np31\n(dp32\n"
            "g7\nS'.1.3.6.1.2.1.25.3.1.17'\np33\nsg9\nS'COM1:'\np34\n"
            "ssS'1'\n(dp35\ng7\nS'.1.3.6.1.2.1.25.3.1.5'\np36\nsg9\n"
            "S'WebEx Document Loader'\np37\nssS'3'\n(dp38\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.5'\np39\nsg9\nS'Lexmark X500 Series'\n"
            "p40\nssS'2'\n(dp41\ng7\nS'.1.3.6.1.2.1.25.3.1.5'\np42\nsg9\n"
            "S'Microsoft XPS Document Writer'\np43\nssS'5'\n(dp44\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.5'\np45\nsg9\nS'HP LaserJet 2100 PCL6'\n"
            "p46\nssS'4'\n(dp47\ng7\nS'.1.3.6.1.2.1.25.3.1.5'\np48\nsg9\n"
            "S'HP LaserJet 3050 Series PCL 6'\np49\nssS'7'\n(dp50\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.4'\np51\nsg9\nS'MS TCP Loopback "
            "interface'\np52\nssS'6'\n(dp53\ng7\nS'.1.3.6.1.2.1.25.3.1.3'\n"
            "p54\nsg9\nS'Intel'\np55\nssS'9'\n(dp56\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.4'\np57\nsg9\nS'VMware Virtual Ethernet "
            "Adapter for VMnet1'\np58\nssS'8'\n(dp59\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.4'\np60\nsg9\nS'VMware Virtual Ethernet "
            "Adapter for VMnet8'\np61\nssstp62\n."
        )

        # Verify that the modeler plugin processes the data properly.
        relmap = self.cmap.process(self.device, results, log)
        self.assertEquals(relmap.relname, "cpus")

        om = relmap.maps[0]
        self.assertEquals(om.compname, "hw")
        self.assertEquals(om.setProductKey.args[0], "Intel")
        self.assertEquals(om.setProductKey.args[1], "Intel")

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, relmap)
        cpu = self.device.hw.cpus()[0]
        self.assertEquals(cpu.getManufacturerName(), "Intel")
        self.assertEquals(cpu.getProductName(), "Intel")

    def testCentOS5Server(self):
        results = loads(
            "((dp1\n(dp2\nS'deviceTableOid'\np3\n(dp4\nS'1025'\np5\n(dp6\n"
            "S'_type'\np7\nS'.1.3.6.1.2.1.25.3.1.4'\np8\nsS'_description'\n"
            "p9\nS'network interface lo'\np10\nssS'768'\np11\n(dp12\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.3'\np13\nsg9\nS'GenuineIntel: Intel(R) "
            "Core(TM)2 CPU         T7400  @ 2.16GHz'\np14\nssS'1026'\np15\n"
            "(dp16\ng7\nS'.1.3.6.1.2.1.25.3.1.4'\np17\nsg9\nS'network "
            "interface eth0'\np18\nssS'1027'\np19\n(dp20\ng7\n"
            "S'.1.3.6.1.2.1.25.3.1.4'\np21\nsg9\nS'network interface sit0'\n"
            "p22\nssS'3072'\np23\n(dp24\ng7\nS'.1.3.6.1.2.1.25.3.1.12'\n"
            "p25\nsg9\nS\"Guessing that there's a floating point "
            'co-processor"\np26\nssstp27\n.'
        )

        # Verify that the modeler plugin processes the data properly.
        relmap = self.cmap.process(self.device, results, log)
        self.assertEquals(relmap.relname, "cpus")

        om = relmap.maps[0]
        self.assertEquals(om.compname, "hw")
        self.assertEquals(om.clockspeed, 2160)
        self.assertEquals(
            om.setProductKey.args[0],
            "GenuineIntel: Intel(R) Core(TM)2 CPU         T7400  @ 2.16GHz",
        )
        self.assertEquals(om.setProductKey.args[1], "Intel")

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, relmap)
        cpu = self.device.hw.cpus()[0]
        self.assertEquals(cpu.clockspeed, 2160)
        self.assertEquals(cpu.getManufacturerName(), "Intel")
        self.assertEquals(
            cpu.getProductName(),
            "GenuineIntel_ Intel(R) Core(TM)2 CPU         T7400  _ 2.16GHz",
        )

    def testGetManufacturerAndModel(self):
        r = getManufacturerAndModel("Unknown CPU Type")
        self.assertEquals(r.args[0], "Unknown CPU Type")
        self.assertEquals(r.args[1], "Unknown")

        r = getManufacturerAndModel("Intel CPU")
        self.assertEquals(r.args[0], "Intel CPU")
        self.assertEquals(r.args[1], "Intel")

        r = getManufacturerAndModel("Xeon")
        self.assertEquals(r.args[0], "Xeon")
        self.assertEquals(r.args[1], "Intel")

        r = getManufacturerAndModel("Opteron Quad-Core")
        self.assertEquals(r.args[0], "Opteron Quad-Core")
        self.assertEquals(r.args[1], "AMD")


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestCpuMap))
    return suite
