##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from DateTime import DateTime
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenModel.BatchDeviceLoader import BatchDeviceLoader


class FakeConfigs:
    pass


class FakeOptions:
    def __init__(self):
        self.nocommit = True
        self.must_be_resolvable = False


class Testzenbatchloader(BaseTestCase):
    def afterSetUp(self):
        super(Testzenbatchloader, self).afterSetUp()

        self.zloader = BatchDeviceLoader(noopts=1)
        self.zloader.options = FakeOptions()
        self.zloader.options.nomodel = True
        self.zloader.options.nocommit = False

        self.log = logging.getLogger("zen.BatchDeviceLoader")
        self.zloader.log = self.log

    def testSampleConfig(self):
        """
        Is the internal sample config still working?
        """
        configs = self.zloader.sample_configs.split("\n")
        device_list, unparseable = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)

    def testCProps(self):
        """
        Verify that we can set custom properties
        """
        olympics = DateTime("2010/02/28")
        configs = ["device1 cDateTest=%s" % repr(olympics)]
        device_list, unparseable = self.zloader.parseDevices(configs)
        self.zloader.processDevices(device_list)

        dev = self.zloader.dmd.Devices.findDevice("device1")
        self.assert_(dev.cDateTest == olympics)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(Testzenbatchloader))
    return suite
