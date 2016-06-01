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

from zExceptions import Redirect

from Products.ZenModel.Exceptions import *
from Products.ZenModel.DeviceClass import *
from Products.ZenModel.Device import Device
from Products.Zuul import getFacade
from ZenModelBaseTest import ZenModelBaseTest

class TestDeviceClass(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestDeviceClass, self).afterSetUp()
        devices = self.dmd.Devices
        self.routers = devices.createOrganizer("/NetworkDevice/Router")
        devices.createOrganizer("/NetworkDevice/Router/Firewall")
        devices.createOrganizer("/NetworkDevice/Router/RSM")
        devices.createOrganizer("/Server")
        self.dev = self.dmd.Devices.createInstance("testdev")
        self.dev2 = self.dmd.Devices.createInstance("testdev2")
        self.dev3 = self.routers.createInstance("testrouter")

    def testCreateInstanceDevice(self):
        devices = self.dmd.Devices
        self.assert_(isinstance(self.dev, Device))
        self.assertEqual(self.dev.deviceClass(), devices)
        self.assertEqual(self.dev.getDeviceClassName(), "/")
        self.assertEqual(devices.countDevices(), 3)
        self.assert_(self.dev in devices.getSubDevices())
        self.assertEqual(devices.getPythonDeviceClass(), Device)

    
    def testCreateInstanceDeviceAndIndex(self):
        devices = self.dmd.Devices
        self.assert_(isinstance(self.dev, Device))
        self.assertEqual(self.dev.deviceClass(), devices)
        self.assertEqual(self.dev.getDeviceClassName(), "/")


    def testSearchDevicesOneDevice(self):
        devices = self.dmd.Devices
        self.assertRaises(Redirect, devices.searchDevices, "testdev2",
                          REQUEST=dict(junk=1))

    
    def testSearchDevicesNoDevice(self):
        devices = self.dmd.Devices
        self.assertEqual(len(devices.searchDevices("adsf")), 0)

    
    def testSearchDevicesMultipleDevices(self):
        devices = self.dmd.Devices
        self.assertEqual(len(devices.searchDevices("testdev*")), 2)

    def testSearchDevicesByTitle(self):
        self.dev2.setTitle('testtitle2')
        foundDevices = self.dmd.Devices.searchDevices('testtitle2')
        self.assertEqual( len( foundDevices ), 1 )
        self.assertEqual( foundDevices[0].id, self.dev2.id )
        
    def testFindExact(self):
        id = 'testdev'
        devices = self.dmd.Devices
        self.assertEqual(len(devices._findDevice(id)), 1)

        dev = devices.findDeviceByIdExact(id)
        self.assertEqual( dev.id, id )
        
        self.assert_( not devices.findDeviceByIdExact(None) )
        self.assert_( not devices.findDeviceByIdExact('badid') )

    def test_FindDevices(self):
        devBrains = self.dmd.Devices._findDevice( 'testdev' )
        self.assertEqual( len( devBrains ), 1 )
        dev = devBrains[0].getObject()
        self.assertEqual( dev.id, 'testdev' )
        dev.setTitle('testdev2')
        devBrains = self.dmd.Devices._findDevice( 'testdev2' )
        self.assertEqual( len( devBrains ), 2 )
        self.assertEqual( devBrains[0].getObject().id, 'testdev2' )
        self.assertEqual( devBrains[1].getObject().id, 'testdev' )
        devBrains = self.dmd.Devices._findDevice( 'testdev2', False )
        self.assertEqual( len(devBrains), 1 )
        self.assertEqual( devBrains[0].getObject().id, 'testdev2' )
        devBrains = self.dmd.Devices._findDevice( 'badid' )
        self.assert_( not devBrains )

    def testFindDevice(self):
        dev = self.dmd.Devices.findDevice( 'testdev' )
        self.assertEqual( dev.id, 'testdev' )
        dev.setTitle('testdev2')
        dev = self.dmd.Devices.findDevice( 'testdev2' )
        self.assertEqual( dev.id, 'testdev2' )
        dev.setTitle( 'testtitle' )
        dev = self.dmd.Devices.findDevice( 'testtitle' )
        self.assertEqual( dev.id, 'testdev2' )
        dev = self.dmd.Devices.findDevice( 'badid' )
        self.assert_( dev is None )


    def testFindDeviceByIdOrIp(self):
        dev = self.dmd.Devices.findDeviceByIdOrIp( 'testdev' )
        self.assertEqual( dev.id, 'testdev' )
        dev.setManageIp( '1.1.1.1' )
        dev = self.dmd.Devices.findDeviceByIdOrIp( '1.1.1.1' )
        self.assertEqual( dev.id, 'testdev' )
        dev = self.dmd.Devices.findDeviceByIdOrIp( 'badid' )
        self.assert_( dev is None )

    def testGetPeerDeviceClassNames(self):
        dcnames = self.dev3.getPeerDeviceClassNames()
        self.assert_("/NetworkDevice/Router" in dcnames)
        self.assert_("/NetworkDevice/Router/Firewall" in dcnames)
        self.assert_("/NetworkDevice/Router/RSM" in dcnames)

        self.routers.moveDevices('/','testrouter')
        self.assert_(self.dev3 in self.dmd.Devices.getSubDevices())
        self.assert_(self.dev3 not in 
            self.dmd.Devices.NetworkDevice.Router.getSubDevices())
                        

    def testZPythonClass(self):
        from Products.ZenModel.tests.CustDevice import CustDevice
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        self.assertEqual(CustDevice, 
                     self.dmd.Devices.CustDev.getPythonDeviceClass())

    def testMoveDevices(self):
        self.dmd.Devices.moveDevices('/Server', 'testdev')
        dev = self.dmd.Devices.Server.devices.testdev
        self.assert_(dev.os.interfaces)

    def testMoveDevicesRetainsGuid(self):
        guid = IGlobalIdentifier(self.dev).getGUID()
        self.dmd.Devices.moveDevices('/Server', 'testdev')
        newguid = IGlobalIdentifier(self.dmd.Devices.Server.devices.testdev).getGUID()
        self.assertEqual(guid, newguid)
        path = self.dmd.guid_table.get(newguid, None)
        self.assertEqual(path, '/zport/dmd/Devices/Server/devices/testdev')

    def testMoveDevicesStandardToCust(self):
        anna = self.dmd.Locations.createOrganizer("Annapolis")
        group = self.dmd.Groups.createOrganizer("TestGroup")
        self.dev.setLocation("/Annapolis")
        self.dev.setGroups("/TestGroup")
        self.dev.rackSlot = 15
        from Products.ZenModel.tests.CustDevice import CustDevice
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        self.dmd.Devices.moveDevices('/CustDev', 'testdev') 
        dev = self.dmd.Devices.findDevice('testdev')
        self.assertEqual(dev.getDeviceClassPath(), "/CustDev")
        self.assertEqual(dev.rackSlot, '15')
        self.assertEqual(dev.__class__, CustDevice)
        self.assertEqual(dev.location(), anna)
        self.assert_(dev in anna.devices())
        self.assert_(group in dev.groups())

    def testMoveDevicesCustToStandard(self):
        custdev = self.dmd.Devices.createOrganizer("/CustDev")
        custdev._setProperty('zPythonClass',
                             'Products.ZenModel.tests.CustDevice')
        cdev = self.dmd.Devices.CustDev.createInstance('cdev')
        anna = self.dmd.Locations.createOrganizer("Annapolis")
        group = self.dmd.Groups.createOrganizer("TestGroup")
        cdev.setLocation("/Annapolis")
        cdev.setGroups("/TestGroup")
        cdev.rackSlot = 15
        self.dmd.Devices.moveDevices("/", 'cdev')
        dev = self.dmd.Devices.findDevice('cdev')
        self.assertEqual(dev.getDeviceClassPath(), "/")
        self.assertEqual(dev.rackSlot, '15')
        self.assertEqual(dev.__class__, Device)
        self.assertEqual(dev.location(), anna)
        self.assert_(group in dev.groups())
     
    def testOrganizer(self):
        devices = self.dmd.Devices
        dc = devices.createOrganizer('/Test')
        self.assert_(dc in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        self.assertEqual(devices.countChildren(), 6)
        self.assert_('Test' in devices.childIds())
        self.assert_('/Test' in devices.getOrganizerNames())
        self.assertEqual(devices.getOrganizer('/Test'), dc)
        layer = devices.createOrganizer('/Layer')
        devices.moveOrganizer('Layer',['Test'])
        self.assert_('/Layer' in devices.getOrganizerNames())
        self.assert_(dc not in devices.children())
        self.assert_(dc in devices.getSubOrganizers())
        getFacade('device', self.dmd).deleteNode('/zport/dmd/Devices/Layer')
        self.assert_(layer not in devices.children())
        self.assert_(dc not in devices.getSubOrganizers())

    def testDeviceOrganizer(self):
        devices = self.dmd.Devices
        dc = devices.createOrganizer('/Test')
        self.assertEqual(devices.countDevices(), 3)
        self.assert_(self.dev in devices.getSubDevices())

    def test_devtypes(self):
        devices = self.dmd.Devices
        # Test registration
        devices.register_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [('Device', 'SNMP')])
        # Test no duplicates
        devices.register_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [('Device', 'SNMP')])
        # Test removal
        devices.unregister_devtype('Device', 'SNMP')
        self.assertEqual(devices.devtypes, [])
        

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDeviceClass))
    return suite

if __name__=="__main__":
    framework()
