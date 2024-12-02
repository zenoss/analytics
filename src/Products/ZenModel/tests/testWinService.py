##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Products.ZenModel.Exceptions import *
from Products.ZenModel.WinService import WinService

from ZenModelBaseTest import ZenModelBaseTest


class TestWinService(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestWinService, self).afterSetUp()

        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = WinService('wsvc')
        self.dev.os.winservices._setObject('wsvc',tmpo)
        self.wsvc = self.dev.os.winservices()[0]
        self.wsvc.dmd = self.dmd #temporary fix -> setServiceClass


    def testSetServiceClass(self):
        """Short test of basic set/get working"""
        svc = {'name':'ALG','description':'testsvc'}
        self.wsvc.setServiceClass(svc)
        self.assert_(self.wsvc.name() == 'ALG')
        self.assert_(self.wsvc.getServiceClass() == svc)
    
    
    def testSetManageIp(self):
        self.wsvc.setManageIp('1.2.3.4/24')
        self.assert_(self.wsvc.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.wsvc.getManageIp() == '2.3.4.5/24')


    def testGets(self):
        self.assert_(self.wsvc.hostname() == 'testdev')
        self.assert_(self.wsvc.getParentDeviceName() == 'testdev')
        self.assert_(self.wsvc.getParentDeviceUrl() == self.dev.absolute_url_path())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWinService))
    return suite

if __name__=="__main__":
    framework()
