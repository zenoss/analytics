##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import zope.interface

from twisted.internet import base, defer

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollectorPreferences,
    IScheduledTask,
    IScheduler,
)
from Products.ZenCollector.tasks import DeviceTaskSplitter
from Products.ZenTestCase.BaseTestCase import BaseTestCase

base.DelayedCall.debug = True


@zope.interface.implementer(ICollectorPreferences)
class TestCollectorConfigurator(object):
    def __init__(self):
        self.collectorName = "test"
        self.defaultRRDCreateCommand = None
        self.cycleInterval = 0  # seconds
        self.configCycleInterval = 0  # minutes
        self.configurationService = "nota"

    def buildOptions(self, parser):
        pass


@zope.interface.implementer(IScheduledTask)
class TestTask(object):
    pass


class TestCollectorDaemon(BaseTestCase):
    def testPingIssues(self):
        """
        Test ping issues handling by validating that the scheduler properly
        pauses and resumes tasks based upon the ping issues results.
        """
        pausedDevices = []
        resumedDevices = []
        testPingIssues = []

        # create a test scheduler that just keeps track of what was paused
        @zope.interface.implementer(IScheduler)
        class PingTestScheduler(object):
            def addTask(self, newTask):
                pass

            def removeTasksForDevice(self, devId):
                pass

            def pauseTasksForDevice(self, devId):
                pausedDevices.append(devId)

            def resumeTasksForDevice(self, devId):
                resumedDevices.append(devId)

        # create a test daemon that lets us just test ping issues
        class PingTestDaemon(CollectorDaemon):
            def __init__(self):
                super(PingTestDaemon, self).__init__(
                    TestCollectorConfigurator, DeviceTaskSplitter, TestTask
                )
                self._scheduler = PingTestScheduler()

            def getDevicePingIssues(self):
                return defer.succeed(testPingIssues)

        # create our test daemon and force the cycle option on so that the
        # maintenance cycle will take place when asked
        daemon = PingTestDaemon()
        daemon.options.cycle = True

        testPingIssues.append(("foobar.zenoss.loc", 1, 3))
        d = daemon._maintenanceCycle()

        # validate that in the first maintenance cycle that foobar.zenoss.loc
        # is paused
        def _allDone1(result):
            self.assertTrue("foobar.zenoss.loc" in pausedDevices)
            self.assertTrue("some fake device" not in pausedDevices)

            # prepare for the second test by clearing all ping issues
            del testPingIssues[:]
            return daemon._maintenanceCycle()

        # validate that foobar.zenoss.loc is now successfully resumed
        def _allDone2(result):
            self.assertTrue("foobar.zenoss.loc" in resumedDevices)
            self.assertTrue("some fake device" not in resumedDevices)

        d.addBoth(_allDone1)
        d.addBoth(_allDone2)
        return d
