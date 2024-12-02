##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.Lockable import UNLOCKED, DELETE_LOCKED, UPDATE_LOCKED

class TestOSProcesses(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestOSProcesses, self).afterSetUp()
        self.dmd.Processes.manage_addOSProcessClass('test')
        self.pclass = self.dmd.Processes.osProcessClasses.test
        self.device = self.dmd.Devices.createInstance('pepe')
        self.device.os.addOSProcess("/".join(self.pclass.getPhysicalPath()), "test", True)
        self.process = self.device.os.processes()[0]


    def beforeTearDown(self):
        super(TestOSProcesses, self).beforeTearDown()

    def testGetsSendEventFromClass(self):
        self.assertIsNone(self.process.sendEventWhenBlockedFlag)

        # if the state is not set on the instance derive it from the class
        self.pclass.setZenProperty("zSendEventWhenBlockedFlag", True)
        self.assertTrue(self.process.sendEventWhenBlocked())
        self.pclass.setZenProperty("zSendEventWhenBlockedFlag", False)
        self.assertFalse(self.process.sendEventWhenBlocked())

        # set it on the instance and make sure that overrides the class
        self.pclass.setZenProperty("zSendEventWhenBlockedFlag", True)
        self.process.sendEventWhenBlockedFlag = False
        self.assertFalse(self.process.sendEventWhenBlocked())

    def testGetsLockingStateFromClass(self):
        self.assertIsNone(self.process.modelerLock)

        # make sure we get it from the class if not set on the instance
        pclass = self.process.osProcessClass()
        pclass.setZenProperty("zModelerLock", UNLOCKED)
        self.assertTrue(self.process.isUnlocked())

        pclass.setZenProperty("zModelerLock", UPDATE_LOCKED)
        pclass.setZenProperty("zSendEventWhenBlockedFlag", UPDATE_LOCKED)
        self.assertFalse(self.process.isUnlocked())
        # setting update sets deletion as well
        self.assertTrue(self.process.isLockedFromDeletion())
        self.assertTrue(self.process.sendEventWhenBlocked())
        self.assertTrue(self.process.isLockedFromUpdates())

        # set it on the instance
        self.process.unlock()
        self.assertFalse(self.process.sendEventWhenBlocked())
        self.assertTrue(self.process.isUnlocked())

    def testResetProcessLocking(self):
        pclass = self.process.osProcessClass()
        pclass.setZenProperty("zModelerLock", UPDATE_LOCKED)

        self.process.unlock()
        self.assertEqual(self.process.modelerLock, 0)
        self.process.lockFromUpdates()
        self.assertEquals(self.process.modelerLock, None)
        
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestOSProcesses))
    return suite
