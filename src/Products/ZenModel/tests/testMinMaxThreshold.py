##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

    
from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
from Products.ZenEvents import Event

class TestMinMaxThreshold(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestMinMaxThreshold, self).afterSetUp()
        device = self.dmd.Devices.createInstance('test-device')
        t = MinMaxThreshold('test')
        self.threshold = t.createThresholdInstance(device)

    def beforeTearDown(self):
        super(TestMinMaxThreshold, self).beforeTearDown()

    def testCheckRange(self):
        result = self.threshold.checkRange('point', None) 
        self.assert_(result == [])

        # minimum is None and maximum is None
        self.threshold.minimum = None
        self.threshold.maximum = None

        ## in bounds
        result = self.threshold.checkRange('point', 0)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 0)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 5)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 5)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point',-5)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == -5)
        self.assert_(result[0]['severity'] == Event.Clear)

        # minimum is None and maximum is not None
        self.threshold.minimum = None
        self.threshold.maximum = 100

        ## in bounds
        result = self.threshold.checkRange('point',-5)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == -5)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 0)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 0)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 5)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 5)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 100)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 100)
        self.assert_(result[0]['severity'] == Event.Clear)

        ## exceeded
        result = self.threshold.checkRange('point', 101)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 101)
        self.assert_(result[0]['how'] == 'exceeded')

        # minimum is not None and maximum is None
        self.threshold.minimum = 100
        self.threshold.maximum = None

        ## in bounds
        result = self.threshold.checkRange('point', 100)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 100)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 101)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 101)
        self.assert_(result[0]['severity'] == Event.Clear)

        ## not met
        result = self.threshold.checkRange('point', 99)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 99)
        self.assert_(result[0]['how'] == 'not met')

        # minimum <= maximum
        self.threshold.minimum = 100
        self.threshold.maximum = 100

        ## in bounds
        result = self.threshold.checkRange('point', 100)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 100)
        self.assert_(result[0]['severity'] == Event.Clear)

        ## exceeded
        result = self.threshold.checkRange('point', 101)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 101)
        self.assert_(result[0]['how'] == 'exceeded')

        ## not met
        result = self.threshold.checkRange('point', 99)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 99)
        self.assert_(result[0]['how'] == 'not met')

        # minimum > maximum
        self.threshold.minimum = 101
        self.threshold.maximum = 99

        ## in bounds
        result = self.threshold.checkRange('point', 101)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 101)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 102)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 102)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 98)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 98)
        self.assert_(result[0]['severity'] == Event.Clear)

        result = self.threshold.checkRange('point', 99)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 99)
        self.assert_(result[0]['severity'] == Event.Clear)

        ## violated
        result = self.threshold.checkRange('point', 100)
        self.assert_(len(result) == 1)
        self.assert_(result[0]['current'] == 100)
        self.assert_(result[0]['how'] == 'violated')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestMinMaxThreshold))
    return suite
