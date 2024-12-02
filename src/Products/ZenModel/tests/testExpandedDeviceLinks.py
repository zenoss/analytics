##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import time
import logging
from zope.interface import implements
from zope.component import getGlobalSiteManager, adapts

from Products.ZenModel.Exceptions import *
from Products.ZenModel.interfaces import IExpandedLinkProvider
from Products.ZenModel.Device import Device, manage_createDevice

from ZenModelBaseTest import ZenModelBaseTest

_TEST_LINK_1 = '<a href="http://localhost:8080">TEST LINK</a>'
_TEST_LINK_2 = '<a href="http://localhost:8080">ANOTHER TEST LINK</a>'

class testExpandedLinkProvider(object):
    implements( IExpandedLinkProvider )
    adapts( Device )

    def __init__(self,context):
        self._context = context

    def getExpandedLinks(self):
        return [_TEST_LINK_1,_TEST_LINK_2]

class TestExpandedDeviceLinks(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestExpandedDeviceLinks, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        
        getGlobalSiteManager().registerSubscriptionAdapter(
            testExpandedLinkProvider)
                 
    def beforeTearDown(self):
        super(TestExpandedDeviceLinks, self).beforeTearDown()
        getGlobalSiteManager().unregisterSubscriptionAdapter(
            testExpandedLinkProvider)

    def testExpandedDeviceLinks(self):
        expandedLinks = self.dev.getExpandedLinks()
        self.assert_(_TEST_LINK_1 in expandedLinks)
        self.assert_(_TEST_LINK_2 in expandedLinks)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestExpandedDeviceLinks))
    return suite

if __name__=="__main__":
    framework()
