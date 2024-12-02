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
from Products.DataCollector.plugins.zenoss.snmp.CiscoMap import CiscoMap
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class TestCiscoMap(BaseTestCase):
    def afterSetUp(self):
        super(TestCiscoMap, self).afterSetUp()
        self.adm = ApplyDataMap()
        self.cmap = CiscoMap()
        self.device = self.dmd.Devices.createInstance("testDevice")

    def testNonAsciiSerial(self):
        results = loads(
            "((dp0\nS'_serialNumber'\np1\nS'"
            "\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'\n"
            "p2\nsS'_memFree'\np3\nL690209880L\nsS'_memUsed'\np4\n"
            "L136548740L\nsS'snmpOid'\np5\nS'.1.3.6.1.4.1.9.1.222'\np6\n"
            "s(dp7\nS'entPhysicalTable'\np8\n(dp9\nstp10\n."
        )

        # Verify that the modeler plugin processes the data properly.
        om = self.cmap.process(self.device, results, log)[0]
        self.assertEquals(om.setHWSerialNumber, "Invalid")

    def testTotalMemory(self):
        results = loads(
            "((dp0\nS'_serialNumber'\np1\n"
            "S'\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff\\xff'\n"
            "p2\nsS'_memFree'\np3\nL690209880L\nsS'_memUsed'\np4\n"
            "L136548740L\nsS'snmpOid'\np5\nS'.1.3.6.1.4.1.9.1.222'\np6\n"
            "s(dp7\nS'entPhysicalTable'\np8\n(dp9\nstp10\n."
        )

        om = self.cmap.process(self.device, results, log)[1]
        self.assertEquals(om.compname, "hw")
        self.assertEquals(om.totalMemory, 826758620)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestCiscoMap))
    return suite
