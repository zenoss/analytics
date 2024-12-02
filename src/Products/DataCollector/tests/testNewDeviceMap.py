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

import mock

from Products.DataCollector.ApplyDataMap import ApplyDataMap
from Products.DataCollector.plugins.zenoss.snmp.NewDeviceMap import (
    NewDeviceMap,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class TestNewDeviceMap(BaseTestCase):
    def afterSetUp(self):
        super(TestNewDeviceMap, self).afterSetUp()
        self.adm = ApplyDataMap()
        self.ndmap = NewDeviceMap()
        self.device = self.dmd.Devices.createInstance("testDevice")
        self.__enterprise_oids_patcher = mock.patch(
            "Products.DataCollector.plugins.zenoss.snmp.NewDeviceMap.EnterpriseOIDs",
            new={
                ".1.3.6.1.4.1.311": "Microsoft",
                ".1.3.6.1.4.1.8072": "net snmp",
            }
        )
        self.__enterprise_oids_patcher.start()
        self.addCleanup(self.__enterprise_oids_patcher.stop)

    def testWin2003Server(self):
        results = loads(
            "((dp1\nS'snmpDescr'\np2\nS'Hardware: x86 Family 15 Model 4 "
            "Stepping 9 AT/AT COMPATIBLE - Software: Windows Version 5.2 "
            "(Build 3790 Uniprocessor Free)'\np3\nsS'snmpOid'\np4\n"
            "S'.1.3.6.1.4.1.311.1.1.3.1.2'\np5\ns(dtp6\n."
        )

        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)
        self.assertEquals(
            om.setHWProductKey.args[0], ".1.3.6.1.4.1.311.1.1.3.1.2"
        )
        self.assertEquals(om.setHWProductKey.args[1], "Microsoft")
        self.assertEquals(om.setOSProductKey, "Windows Version 5.2")
        self.assertEquals(
            om.snmpDescr,
            "Hardware: x86 Family 15 Model 4 Stepping 9 AT/AT COMPATIBLE "
            "- Software: Windows Version 5.2 (Build 3790 Uniprocessor Free)",
        )
        self.assertEquals(om.snmpOid, ".1.3.6.1.4.1.311.1.1.3.1.2")

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, om)
        self.assertEquals(self.device.getHWManufacturerName(), "Microsoft")
        self.assertEquals(
            self.device.getHWProductName(), ".1.3.6.1.4.1.311.1.1.3.1.2"
        )
        self.assertEquals(self.device.getOSManufacturerName(), "Unknown")
        self.assertEquals(
            self.device.getOSProductName(), "Windows Version 5.2"
        )
        self.assertEquals(
            self.device.snmpDescr,
            "Hardware: x86 Family 15 Model 4 Stepping 9 AT/AT COMPATIBLE "
            "- Software: Windows Version 5.2 (Build 3790 Uniprocessor Free)",
        )
        self.assertEquals(self.device.snmpOid, ".1.3.6.1.4.1.311.1.1.3.1.2")

    def testCentOS5Server(self):
        results = loads(
            "((dp1\nS'snmpDescr'\np2\nS'Linux centos32.damsel.loc "
            "2.6.18-128.1.6.el5 #1 SMP Wed Apr 1 09:19:18 EDT 2009 i686'\n"
            "p3\nsS'snmpOid'\np4\nS'.1.3.6.1.4.1.8072.3.2.10'\np5\ns(dtp6\n."
        )

        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)
        self.assertEquals(
            om.setHWProductKey.args[0], ".1.3.6.1.4.1.8072.3.2.10"
        )
        self.assertEquals(om.setHWProductKey.args[1], "net snmp")
        self.assertEquals(om.setOSProductKey, "Linux 2.6.18-128.1.6.el5")
        self.assertEquals(
            om.snmpDescr,
            "Linux centos32.damsel.loc 2.6.18-128.1.6.el5 #1 SMP Wed "
            "Apr 1 09:19:18 EDT 2009 i686",
        )
        self.assertEquals(om.snmpOid, ".1.3.6.1.4.1.8072.3.2.10")

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, om)
        self.assertEquals(self.device.getHWManufacturerName(), "net snmp")
        self.assertEquals(
            self.device.getHWProductName(), ".1.3.6.1.4.1.8072.3.2.10"
        )
        self.assertEquals(self.device.getOSManufacturerName(), "Unknown")
        self.assertEquals(
            self.device.getOSProductName(), "Linux 2.6.18-128.1.6.el5"
        )
        self.assertEquals(
            self.device.snmpDescr,
            "Linux centos32.damsel.loc 2.6.18-128.1.6.el5 #1 SMP Wed "
            "Apr 1 09:19:18 EDT 2009 i686",
        )
        self.assertEquals(self.device.snmpOid, ".1.3.6.1.4.1.8072.3.2.10")

    def testSolaris(self):
        results = loads(
            "((dp1\nS'snmpDescr'\np2\nS'SunOS testHost 5.10 "
            "Generic_138889-05 i86pc'\np3\nsS'snmpOid'\np4\n"
            "S'.1.3.6.1.4.1.8072.3.2.3'\np5\ns(dtp6\n."
        )

        # Verify that the modeler plugin processes the data properly.
        om = self.ndmap.process(self.device, results, log)

        # Verify that the data made it into the model properly.
        self.adm._applyDataMap(self.device, om)
        self.assertEquals(self.device.getOSManufacturerName(), "Sun")
        self.assertEquals(
            self.device.getOSProductName(), "SunOS 5.10 Generic_138889-05"
        )


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestNewDeviceMap))
    return suite
