##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os, sys
from Products.ZenModel.ValueChangeThreshold import ValueChangeThresholdInstance
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenUtils.mock import MockObject

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))



class TestValueChangeThreshold(ZenModelBaseTest):
    def testImpl(self):
        mKey=MockObject(return__="testKey")
        context = MockObject(key=mKey)
        threshold = ValueChangeThresholdInstance("testThrehold",context,'','/Status/Perf', 4)
        # First data point. Should save the value, but generate no event.
        events = threshold._checkImpl("testDataPoint", 1.0)
        self.assertIsNotNone(events)
        self.assertEquals(0,len(events))

        # Check that a duplicate data point generates no event.
        events = threshold._checkImpl("testDataPoint", 1.0)
        self.assertIsNotNone(events)
        self.assertEquals(0,len(events))

        # Check that a modified data point generates an event.
        events = threshold._checkImpl("testDataPoint", 2.0)
        self.assertIsNotNone(events)
        self.assertEquals(1,len(events))
        event = events[0]
        self.assertEquals(2.0, event['current'])
        self.assertEquals(1.0   , event['previous'])
        self.assertEquals('testThrehold', event['eventKey'])
        self.assertEquals(4, event['severity'])
        self.assertEquals('/Status/Perf', event['eventClass'])



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestValueChangeThreshold))
    return suite
