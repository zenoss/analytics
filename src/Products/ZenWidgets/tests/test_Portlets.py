##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json

from Products import Zuul
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenWidgets.browser.Portlets import ProductionStatePortletView


class TestPortlets(BaseTestCase):
    def afterSetUp(self):
        super(TestPortlets, self).afterSetUp()
        self.facade = Zuul.getFacade("device", self.dmd)

    def test_ProductionStatePortletView(self):
        # Create some devices
        devices = self.dmd.Devices
        test_device_maintenance = devices.createInstance(
            "testDeviceMaintenance"
        )
        test_device_production = devices.createInstance("testDeviceProduction")
        test_device_maintenance.setProdState(300)
        test_device_production.setProdState(1000)

        psPortlet = ProductionStatePortletView(self.dmd, self.dmd.REQUEST)

        # filter by maintenance
        result = json.loads(psPortlet())
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(
            result["data"][0]["Device"],
            test_device_maintenance.getPrettyLink(),
        )

        # filter by production
        result = json.loads(psPortlet("Production"))
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(
            result["data"][0]["Device"], test_device_production.getPrettyLink()
        )

        # filter by both
        result = json.loads(psPortlet(["Production", "Maintenance"]))
        self.assertEqual(len(result["data"]), 2)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestPortlets))
    return suite
