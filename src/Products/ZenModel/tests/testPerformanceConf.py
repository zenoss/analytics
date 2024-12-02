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

from Products.ZenModel.PerformanceConf import PerformanceConf, manage_addPerformanceConf

from ZenModelBaseTest import ZenModelBaseTest


class TestPerformanceConf(ZenModelBaseTest):

    def createPerformanceConf(self, collectorName ):
        manage_addPerformanceConf( self.dmd.Monitors.Performance,
                                          collectorName )
        self.assert_( hasattr( self.dmd.Monitors.Performance, collectorName ) )
        return getattr( self.dmd.Monitors.Performance, collectorName )

    def testAddPerformanceConf(self):
        collectorName = 'testcollector'
        conf = self.createPerformanceConf( collectorName )
        self.assertEquals( conf.id, collectorName )

#    def testCreateDeviceWithNoDiscover(self):
#        conf = self.createPerformanceConf( 'testcollector' )
#        deviceName = 'testdevice'
#        createArgs = dict(
#        devicePath = '/Server',
#        tag = 'testtag',
#        serialNumber = 'testno',
#        zSnmpCommunity = 'testcommunity',
#        zSnmpPort=1,
#        zSnmpVer='2c',
#        rackSlot=4,
#        productionState=500,
#        comments='testcomment',
#        hwManufacturer='testhwmanufacturer',
#        hwProductName = 'testhwproductname',
#        osManufacturer = 'testosmanufacturer',
#        osProductName = 'testOsProductName',
#        locationPath = '/',
#        groupPaths = ['/'],
#        systemPaths = ['/'],
#        performanceMonitor = conf.id, #SEEMS GOOFY TO HAVE TO PASS THE MONITOR TO ITSELF
#        discoverProto='none',
#        priority=2,
#        manageIp='1.1.1.1' )
#        device = conf.createDevice( None, #THE CONTEXT ARG IS NOT USED!
#                                    deviceName, 
#                                    **createArgs )
#        self.assert_( device is not None )
#        self.assertEquals( device.id, deviceName )
#        self.assertEquals( device.manageIp, createArgs['manageIp'] )
#        self.assertEquals( device.hw.tag, createArgs['tag'] )
#        self.assertEquals( device.hw.serialNumber, createArgs['serialNumber'] )
#        self.assertEquals( device.zSnmpCommunity, createArgs['zSnmpCommunity'] )
#        self.assertEquals( device.zSnmpPort, createArgs['zSnmpPort'] )
#        self.assertEquals( device.zSnmpVer, createArgs['zSnmpVer'] )
#        self.assertEquals( device.rackSlot, createArgs['rackSlot'] )
#        self.assertEquals( device.comments, createArgs['comments'] )
#        self.assertEquals( device.hw.getManufacturerName(), createArgs['hwManufacturer'] )
#        self.assertEquals( device.hw.getProductName(), createArgs['hwProductName'] )
#        self.assertEquals( device.os.getManufacturerName(), createArgs['osManufacturer'] )
#        self.assertEquals( device.os.getProductName(), createArgs['osProductName'] )
#        self.assertEquals( device.getPriority(), createArgs['priority'] )
#        self.assertEquals( device.location(), self.dmd.Locations.getOrganizer( 
#                                                createArgs[ 'locationPath' ] ) )
#        varGroups = Set( device.groups() )
#        controlGroups = Set( [ self.dmd.Groups.getOrganizer( path ) for path in 
#                                                createArgs[ 'groupPaths' ] ] )
#        self.assertEquals( varGroups, controlGroups  )
#        varSystems = Set( device.systems() )
#        controlSystems = Set( [ self.dmd.Systems.getOrganizer( path ) for path in 
#                                                createArgs[ 'systemPaths' ] ] )
#        self.assertEquals( varSystems, controlSystems  )
                           
                
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPerformanceConf))
    return suite

if __name__=="__main__":
    framework()
