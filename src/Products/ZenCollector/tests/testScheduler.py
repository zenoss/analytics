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
from Products.ZenCollector.scheduler import Scheduler
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.observable import ObservableMixin


@zope.interface.implementer(IScheduledTask)
class BasicTestTask(ObservableMixin):
    def __init__(self):
        super(BasicTestTask, self).__init__()
        self.name = "BasicTestTask"
        self.interval = 60
        self.state = "IDLE"
        self.missedRuns = 0
        self.totalRuns = 0
        self.cleaned = False

    def doTask(self):
        pass

    def cleanup(self):
        self.cleaned = True


class TestScheduler(BaseTestCase):
    def testDeleteTasks(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myDevice:myTask1"
        myTask1.configId = "myDevice"

        myTask2 = BasicTestTask()
        myTask2.name = "myDevice:myTask2"
        myTask2.configId = "myDevice"

        myTask3 = BasicTestTask()
        myTask3.name = "myDevice2:myTask3"
        myTask3.configId = "myDevice2"

        scheduler = Scheduler()
        scheduler.addTask(myTask1)
        scheduler.addTask(myTask2)
        scheduler.addTask(myTask3)
        self.assertEquals(len(scheduler._tasks), 3)
        self.assertTrue(myTask1.name in scheduler._tasks)
        self.assertTrue(myTask2.name in scheduler._tasks)
        self.assertTrue(myTask3.name in scheduler._tasks)

        scheduler.removeTasksForConfig("myDevice")
        self.assertEquals(len(scheduler._tasks), 1)
        self.assertFalse(myTask1.name in scheduler._tasks)
        self.assertFalse(myTask2.name in scheduler._tasks)
        self.assertTrue(myTask3.name in scheduler._tasks)

    def testTaskDoneCallback(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myTask1"
        myTask1.configId = "myTask1"

        def myCallback(taskName):
            self.assertEquals(taskName, myTask1.name)

        scheduler = Scheduler()
        scheduler.addTask(myTask1, myCallback)

    def testTaskCleanup(self):
        myTask1 = BasicTestTask()
        myTask1.name = "myTask1.1"
        myTask1.configId = "myTask1"

        myTask2 = BasicTestTask()
        myTask2.name = "myTask1.2"
        myTask2.configId = "myTask1"
        myTask2.state = "DOING_SOMETHING"  # keep this task from being cleaned

        scheduler = Scheduler()
        scheduler.addTask(myTask1)
        scheduler.addTask(myTask2)

        self.assertTrue(scheduler._isTaskCleanable(myTask1))
        self.assertFalse(scheduler._isTaskCleanable(myTask2))

        # call cleanupTasks directly so we don't have to wait for a
        # looping call to start it
        self.assertFalse(myTask1.cleaned)
        self.assertFalse(myTask2.cleaned)
        scheduler.removeTasksForConfig(myTask1.configId)
        scheduler._cleanupTasks()
        self.assertTrue(myTask1.cleaned)
        self.assertFalse(myTask2.cleaned)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestScheduler))
    return suite
