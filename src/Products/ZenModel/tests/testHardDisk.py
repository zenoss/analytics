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
from Products.ZenModel.HardDisk import HardDisk

from ZenModelBaseTest import ZenModelBaseTest

class TestHardDisk(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestHardDisk, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        tmpo = HardDisk('hdd')
        self.dev.hw.harddisks._setObject('hdd',tmpo)
        self.hdd = self.dev.hw.harddisks()[0]
        self.hdd.description = 'hdd'

    def testSetManageIp(self):
        self.hdd.setManageIp('1.2.3.4/24')
        self.assert_(self.hdd.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')
        self.dev.setManageIp('2.3.4.5/24')
        self.assert_(self.hdd.getManageIp() == '2.3.4.5/24')
        

    def testGets(self):
        self.assert_(self.hdd.getInstDescription() == 'hdd')
        self.assert_(self.hdd.name() == 'hdd')
        self.assert_(self.hdd.hostname() == 'testdev')
        self.assert_(self.hdd.getParentDeviceName() == 'testdev')
        self.assert_(self.hdd.getParentDeviceUrl() == self.dev.absolute_url_path())

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestHardDisk))
    return suite

if __name__=="__main__":
    framework()
