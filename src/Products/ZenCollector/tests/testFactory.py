##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenTestCase.BaseTestCase import BaseTestCase

from ..frameworkfactory import CoreCollectorFrameworkFactory
from ..config import ConfigurationProxy
from ..scheduler import TaskScheduler


class TestFactory(BaseTestCase):
    def testFactoryInstall(self):
        """
        Test to ensure the core factory returns the objects it should.
        """
        factory = CoreCollectorFrameworkFactory()

        configProxy = factory.getConfigurationProxy()
        self.assertTrue(isinstance(configProxy, ConfigurationProxy))

        scheduler = factory.getScheduler()
        self.assertTrue(isinstance(scheduler, TaskScheduler))


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestFactory))
    return suite
