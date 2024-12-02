##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import sys

if __name__ == "__main__":
    execfile(os.path.join(sys.path[0], "framework.py"))

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestCollectorConfig(BaseTestCase):
    def afterSetUp(self):
        super(TestCollectorConfig, self).afterSetUp()

        self._devices = []

        device = self.dmd.Devices.createInstance("testdev1")
        device.zFoobar = True
        self._devices.append(device)

        device = self.dmd.Devices.createInstance("testdev2")
        device.zFoobar = False
        self._devices.append(device)

        device = self.dmd.Devices.createInstance("testdev3")
        self._devices.append(device)

    def testFilter(self):
        class MyCollectorConfig(CollectorConfigService):
            def __init__(self):
                attrs = ("zFooBar", "zWoot")
                CollectorConfigService.__init__(
                    self, self.dmd, "localhost", attrs
                )

            def _filterDevice(self, device):
                return getattr(device, "zFooBar", False)

        _ = MyCollectorConfig()

        self.assertTrue(False)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestCollectorConfig))
    return suite


if __name__ == "__main__":
    framework()  # noqa F821
