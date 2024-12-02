##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from random import shuffle
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.Zuul.utils import getZProperties, mutateRPN

class Item(object):
    def __init__(self, num):
        self.num = num
    def __repr__(self):
        return '<%s>' % self.num


class UtilsTest(BaseTestCase):
    
    def test_canGetAllZProperties(self):
        """Makes sure we are only getting the properties that are defined
        on our object
        """
        testPropertyId = self.dmd.Devices.zenPropertyIds()[0]
        properties = getZProperties(self.dmd.Devices)
        
        # test the results
        self.assertTrue(isinstance(properties, dict))
        self.assertTrue(testPropertyId in properties,
                        'testPropertyId should be a key in the returned dictionary')

    def test_canGetGroupSpecificZProperties(self):
        """Makes sure if we override a zproperty at a level that we
        only return that specific zProperty
        """
        devices = self.dmd.Devices
        (testProperty, invariant) = getZProperties(devices).keys()[0:2]
        
        organizer = devices.createOrganizer('TestOrganizer')
        organizer._setProperty(testProperty, 'testChangedProperty')

        properties = getZProperties(organizer)
        self.assertTrue(testProperty in properties.keys() ,
                        "testProperty should be in the list because we changed it")
                
        self.assertFalse(invariant in properties.keys(),
                         "invariant should NOT be in the properties because we did not change it")
        self.assertNotEqual(devices.getProperty(testProperty), organizer.getProperty(testProperty),
                            "Organizers property should have changed")

    def test_RPNMutate(self):
        prefix = "test"
        knownDatapointNames = ["test dp1", "test dp2", "test dp3"]
        RPNs = {
            "dp1,/,100,*": "test dp1,/,100,*",
            "dp4,/,100,*": "dp4,/,100,*",
            "dp2,+,dp1,/,dp4,-,100,*": "test dp2,+,test dp1,/,dp4,-,100,*"
        }

        for rpn, expectedResult in RPNs.iteritems():
            result = mutateRPN(prefix, knownDatapointNames, rpn)
            self.assertEquals(result, expectedResult)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(UtilsTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
