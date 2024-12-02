##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import zope.interface

from Products.ZenCollector.interfaces import IScheduledTask
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenCollector.tasks import SimpleTaskSplitter, SimpleTaskFactory
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.observable import ObservableMixin


class DummyObject(DeviceProxy):
    pass


@zope.interface.implementer(IScheduledTask)
class BasicTestTask(ObservableMixin):
    def __init__(self, name, configId, interval, config):
        self.name = name
        self.configId = configId
        self.interval = interval
        self.config = config

    def doTask(self):
        pass


class TestSplitter(BaseTestCase):
    def testName(self):
        configs = []
        c = DummyObject()
        c.id = "host1"
        c.configCycleInterval = 30
        configs.append(c)

        c = DummyObject()
        c.id = "host2"
        c.configCycleInterval = 100
        configs.append(c)

        taskFactory = SimpleTaskFactory(BasicTestTask)
        taskSplitter = SimpleTaskSplitter(taskFactory)
        tasks = taskSplitter.splitConfiguration(configs)
        self.assertEquals(len(tasks), 2)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestSplitter))
    return suite
