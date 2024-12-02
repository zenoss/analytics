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

from ZenModelBaseTest import ZenModelBaseTest

log = logging.getLogger("zen.IpAddress")
log.warn = lambda *args, **kwds: None

class TestIpInterface(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestIpInterface, self).afterSetUp()
        tmpo = IpInterface('test')
        self.dev = self.dmd.Devices.createInstance('testdev')
        self.dev.os.interfaces._setObject('test',tmpo)
        self.iface = self.dev.getDeviceComponents()[0]
        self.iface.interfaceName = 'test'
        self.iface.macaddress = '00:00:00:00:00:00'


    def testAddIpAddress(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#2 birds...
        self.assert_(self.iface.getIp() == '1.2.3.4')#and 3
        
        self.iface.addIpAddress('2.3.4.5')
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')#it's primary
        self.assert_(self.iface.getIp() == '1.2.3.4')#ditto
        
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_('1.2.3.4/24' not in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '2.3.4.5/24')#primary changed
        self.assert_(self.iface.getIp() == '2.3.4.5')#ditto

    def testGetInterfaceMacaddress(self):
        self.assert_(self.iface.getInterfaceMacaddress() == '00:00:00:00:00:00')
        

    def testViewName(self):
        self.assert_(self.iface.viewName() == 'test')
        self.assert_(self.iface.getInterfaceName() == 'test')


    def testGetIpAddressObjs(self):
        self.iface.addIpAddress("1.2.3.4")
        add = self.dmd.Networks.findIp('1.2.3.4')
        self.assert_(self.iface.getIpAddressObj() == add)
        self.assert_(add in self.iface.getIpAddressObjs())
        self.iface.addIpAddress("2.3.4.5")
        add2 = self.dmd.Networks.findIp('2.3.4.5')
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj() == add)
        self.iface.removeIpAddress('1.2.3.4')
        self.assert_(add2 in self.iface.getIpAddressObjs())
        self.assert_(add not in self.iface.getIpAddressObjs())
        self.assert_(self.iface.getIpAddressObj() == add2)


    def testAddIpaddress(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        

    def testAddLocalIpAddresses(self):
        self.iface.addLocalIpAddress('127.0.0.2')
        self.assert_(self.dmd.Networks.findIp('127.0.0.2') is None)
        self.assert_('127.0.0.2/24' in self.iface._ipAddresses)

    def testGetNetworkName(self):
        self.iface.addIpAddress('1.2.3.4')
        self.assert_(self.iface.getNetworkName() == '1.2.3.0/24')
        

    def testSetIpAddresses(self):
        self.iface.setIpAddresses('1.2.3.4/24')
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')
        
    def testSetIpAddresses2(self):
        self.iface.setIpAddresses(['1.2.3.4/24', '2.3.4.5/24'])
        self.assert_(self.dmd.Networks.findIp('1.2.3.4'))
        self.assert_(self.dmd.Networks.findIp('2.3.4.5'))
        self.assert_('1.2.3.4/24' in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '1.2.3.4/24')
        
        self.iface.setIpAddresses(['2.3.4.5/24', '3.4.5.6/24'])
        self.assert_('1.2.3.4/24' not in self.iface.getIpAddresses())
        self.assert_('2.3.4.5/24' in self.iface.getIpAddresses())
        self.assert_('3.4.5.6/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '2.3.4.5/24')
        
        self.iface.setIpAddresses(['4.5.6.7/24'])
        self.assert_('2.3.4.5/24' not in self.iface.getIpAddresses())
        self.assert_('3.4.5.6/24' not in self.iface.getIpAddresses())
        self.assert_('4.5.6.7/24' in self.iface.getIpAddresses())
        self.assert_(self.iface.getIpAddress() == '4.5.6.7/24')

        self.iface.setIpAddresses([])
        self.assert_(self.iface.getIpAddresses() == [])
        self.assert_(self.iface.getIpAddress() == None)

        self.iface.setIpAddresses('127.0.0.1/8')
        self.assert_(self.iface.getIpAddress() == '127.0.0.1/8')
        self.assert_('127.0.0.1/8' in self.iface.getIpAddressObjs())


    def testGetParentInfo(self):
        self.assert_(self.iface.getParentDeviceName()==self.dev.getDeviceName())
        self.assert_(self.iface.getParentDeviceUrl() == self.dev.absolute_url_path())


    def testClearIps(self):
        self.iface.clearIps(None)
        self.assert_(not self.iface.getIpAddresses())


    def testGetRRDTemplates(self):
        matrix = [
            [   'ethernetCsmacd', [
                ['ethernetCsmacd',      'ethernetCsmacd'],
                ['ethernetCsmacd_64',   'ethernetCsmacd'],
                ['propVirtual',         'ethernetCsmacd'],
                ['propVirtual_64',      'ethernetCsmacd']]
            ],[ 'ethernetCsmacd_64', [
                ['ethernetCsmacd',      'ethernetCsmacd'],
                ['ethernetCsmacd_64',   'ethernetCsmacd_64'],
                ['propVirtual',         'ethernetCsmacd'],
                ['propVirtual_64',      'ethernetCsmacd_64']]
            ],[ 'propVirtual', [
                ['ethernetCsmacd',      'ethernetCsmacd'],
                ['ethernetCsmacd_64',   'ethernetCsmacd_64'],
                ['propVirtual',         'propVirtual'],
                ['propVirtual_64',      'ethernetCsmacd_64']]
            ],[ 'propVirtual_64', [
                ['ethernetCsmacd',      'ethernetCsmacd'],
                ['ethernetCsmacd_64',   'ethernetCsmacd_64'],
                ['propVirtual',         'propVirtual'],
                ['propVirtual_64',      'propVirtual_64']]
            ]
        ]

        for name, tests in matrix:
            self.dmd.Devices.manage_addRRDTemplate(name)
            for iftype, template_id in tests:
                self.iface.type = iftype
                self.assertEquals(
                    template_id, self.iface.getRRDTemplates()[0].id)

    def testProductionState(self):
        # test acquisition from device
        self.dev._setProductionState(400)
        self.assertEquals(self.iface.getProductionState(), 400)

        # test setting directly on the component
        self.iface._setProductionState(100)
        self.assertEquals(self.iface.getProductionState(), 100)
        self.assertEquals(self.dev.getProductionState(), 400)

        # setting it on the component stops it from acquiring from the device
        self.dev._setProductionState(1000)
        self.assertEquals(self.iface.getProductionState(), 100)

        # delete it from the component and it goes back to acquiring
    	self.iface.resetProductionState()
        self.dev._setProductionState(99)
        self.assertEquals(self.iface.getProductionState(), 99)

    # Same as testProductionState but use the property instead of the methods
    def testProductionStateProperty(self):
        # test acquisition from device
        self.dev._setProductionState(400)
        self.assertEquals(self.iface.productionState, 400)

        # test setting directly on the component
        self.iface.productionState = 100
        self.assertEquals(self.iface.productionState, 100)
        self.assertEquals(self.iface.getProductionState(), 100)
        self.assertEquals(self.dev.getProductionState(), 400)

        # setting it on the component stops it from acquiring from the device
        self.dev._setProductionState(1000)
        self.assertEquals(self.iface.productionState, 100)

        # delete it from the component and it goes back to acquiring
        del self.iface.productionState
        self.dev._setProductionState(99)
        self.assertEquals(self.iface.productionState, 99)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestIpInterface))
    return suite

if __name__=="__main__":
    framework()
