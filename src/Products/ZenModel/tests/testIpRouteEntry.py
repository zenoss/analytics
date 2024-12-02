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

from Products.ZenModel.Exceptions import *
from Products.ZenModel.IpInterface import IpInterface
from Products.ZenModel.IpRouteEntry import IpRouteEntry

from ZenModelBaseTest import ZenModelBaseTest

log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None


class TestIpRouteEntry(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestIpRouteEntry, self).afterSetUp()

        self.dev = self.dmd.Devices.createInstance('testdev')

        tmpo = IpInterface('iface0')
        self.dev.os.interfaces._setObject('iface0',tmpo)
        self.iface0 = self.dev.os.interfaces._getOb('iface0')
        self.iface0.setIpAddresses('1.2.3.4/24')
        self.iface0.ifindex = 0
        self.iface0.interfaceName = 'iface0'

        tmpo = IpInterface('iface1')
        self.dev.os.interfaces._setObject('iface1',tmpo)
        self.iface1 = self.dev.os.interfaces._getOb('iface1')
        self.iface1.setIpAddresses('2.3.4.5/24')
        self.iface1.ifindex = 1
        self.iface1.interfaceName = 'iface1'

        tmpo = IpRouteEntry('rEntry')
        self.dev.os.routes._setObject('rEntry',tmpo)
        self.rEntry = self.dev.os.routes()[0]


    def testSetManageIp(self):
        self.rEntry.setManageIp('1.2.3.4/24')
        self.assert_(self.rEntry.getManageIp() == '1.2.3.4/24')
        self.assert_(self.iface0.getManageIp() == '1.2.3.4/24')
        self.assert_(self.iface1.getManageIp() == '1.2.3.4/24')
        self.assert_(self.dev.getManageIp() == '1.2.3.4/24')


    def testSetNextHopIp(self):
        # Deprecated we dont create an IPAdress obj for the next hop anymore
        self.assertEqual(True, True)


    def testSetTarget(self):
        self.rEntry.setTarget('1.2.3.0/24')
        self.assertEqual(self.rEntry.getTarget(), '1.2.3.0/24')
        self.assert_(self.rEntry.matchTarget('1.2.3.0'))
        self.assertEqual(self.rEntry.getTargetIp(), '1.2.3.0')
        self.assertEqual(self.rEntry.getTargetLink(), '<a href="/zport/dmd/Networks/1.2.3.0">1.2.3.0/24</a>')
        #TODO(?): test setTarget locally


    def testSetInterfaceIndex(self):
        self.rEntry.setInterfaceIndex(0)
        self.assertEqual(self.rEntry.getInterfaceIndex(), 0)
        self.assertEqual(self.rEntry.getInterfaceName(), 'iface0')
        self.assertEqual(self.rEntry.getInterfaceIp(), '1.2.3.4')

        self.rEntry.setInterfaceIndex(1)
        self.assertEqual(self.rEntry.getInterfaceIndex(), 1)
        self.assertEqual(self.rEntry.getInterfaceName(), 'iface1')
        self.assertEqual(self.rEntry.getInterfaceIp(), '2.3.4.5')


    def testSetInterfaceName(self):
        self.rEntry.setInterfaceName('iface0')
        self.assertEqual(self.rEntry.getInterfaceIndex(), 0)
        self.assertEqual(self.rEntry.getInterfaceName(), 'iface0')
        self.assertEqual(self.rEntry.getInterfaceIp(), '1.2.3.4')

        self.rEntry.setInterfaceName('iface1')
        self.assertEqual(self.rEntry.getInterfaceIndex(), 1)
        self.assertEqual(self.rEntry.getInterfaceName(), 'iface1')
        self.assertEqual(self.rEntry.getInterfaceIp(), '2.3.4.5')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpRouteEntry))
    return suite

if __name__=="__main__":
    framework()
