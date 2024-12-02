##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.ZDeviceLoader import BaseDeviceLoader


class TestDeviceLoader(ZenModelBaseTest):

    def testCreateDeviceWithNoDiscover(self):
        loader = BaseDeviceLoader(self.dmd)
        deviceName = 'testdevice'
        devicePath = '/Server'
        discoverProto='none'
        performanceMonitor = 'localhost'
        manageIp='1.1.1.1'
        devProps = dict(
            tag = 'testtag',
            serialNumber = 'testno',
            rackSlot=4,
            productionState=500,
            comments='testcomment',
            hwManufacturer='testhwmanufacturer',
            hwProductName = 'testhwproductname',
            osManufacturer = 'testosmanufacturer',
            osProductName = 'testOsProductName',
            locationPath = '/',
            groupPaths = ['/'],
            systemPaths = ['/'],
            priority=2)
        zProps = dict(
            zSnmpCommunity = 'testcommunity',
            zSnmpPort=1,
            zSnmpVer='2c',
        )
        device = loader.load_device(deviceName, devicePath, discoverProto,
                                    performanceMonitor, manageIp, zProps,
                                    devProps)

        self.assert_( device is not None )
        self.assertEquals( device.id, deviceName )
        self.assertEquals( device.manageIp, manageIp )
        self.assertEquals( device.hw.tag, devProps['tag'] )
        self.assertEquals( device.hw.serialNumber, devProps['serialNumber'] )
        self.assertEquals( device.zSnmpCommunity, zProps['zSnmpCommunity'] )
        self.assertEquals( device.zSnmpPort, zProps['zSnmpPort'] )
        self.assertEquals( device.zSnmpVer, zProps['zSnmpVer'] )
        self.assertEquals( device.rackSlot, devProps['rackSlot'] )
        self.assertEquals( device.comments, devProps['comments'] )
        self.assertEquals( device.hw.getManufacturerName(), devProps['hwManufacturer'] )
        self.assertEquals( device.hw.getProductName(), devProps['hwProductName'] )
        self.assertEquals( device.os.getManufacturerName(), devProps['osManufacturer'] )
        self.assertEquals( device.os.getProductName(), devProps['osProductName'] )
        self.assertEquals( device.getPriority(), devProps['priority'] )
        self.assertEquals( device.location(), self.dmd.Locations.getOrganizer( 
                                                devProps[ 'locationPath' ] ) )
        varGroups = set( device.groups() )
        controlGroups = set( self.dmd.Groups.getOrganizer( path ) for path in 
                                                devProps[ 'groupPaths' ] )
        self.assertEquals( varGroups, controlGroups  )
        varSystems = set( device.systems() )
        controlSystems = set( self.dmd.Systems.getOrganizer( path ) for path in 
                                                devProps[ 'systemPaths' ] )
        self.assertEquals( varSystems, controlSystems  )
                           
                
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceLoader))
    return suite

if __name__=="__main__":
    framework()
