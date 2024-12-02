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

import logging

from Products.ZenModel.IpInterface import IpInterface
from Products.AdvancedQuery import Eq
from ZenModelBaseTest import ZenModelBaseTest


log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None


class TestIpAddress(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestIpAddress, self).afterSetUp()
        self.dev = self.dmd.Devices.createInstance("testdev")
        self.dev.setManageIp('2.3.4.5')
        self.maddr = self.dev.ipaddress().primaryAq()
        tmpIface = IpInterface('test')
        self.dev.os.interfaces._setObject('test',tmpIface)
        self.iface = self.dev.getDeviceComponents()[0]
        self.iface.addIpAddress('1.2.3.4')
        self.addr = self.iface.getIpAddressObj()


    def testGets(self):#most/all of the get method tests
        self.assert_(self.addr.getIp() == '1.2.3.4')
        self.assert_(self.addr.getIpAddress() == '1.2.3.4/24')
        self.assert_(self.addr.getInterfaceName() == self.addr.interface().name())
        self.assert_(self.addr.getDeviceUrl() == '/zport/dmd/Devices/devices/testdev')
        self.assert_(self.addr.device() == self.dev)


    def testSetNetmask(self):
        self.addr.setNetmask(8)
        self.assert_(self.addr.getIpAddress() == '1.2.3.4/8')


    def testDeviceDelete(self):
        maddrPath = self.maddr.getPrimaryId()
        addrPath = self.addr.getPrimaryId()
        self.dev.deleteDevice()
        self.assert_(self.maddr.manageDevice() is None)
        self.assert_(self.addr.interface() is None)


#    def testSetIpAddress(self):
#        self.addr.setIpAddress('2.3.4.5/16')
#        self.assert_(self.addr.getIpAddress() == '2.3.4.5/16')

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpAddress))
    return suite
