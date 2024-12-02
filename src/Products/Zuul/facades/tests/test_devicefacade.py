##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from zope.interface.verify import verifyClass
from zope.event import notify
from Products import Zuul
from Products.Zuul.tests.base import ZuulFacadeTestCase
from Products.Zuul.interfaces import IDeviceInfo
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.infos.device import DeviceInfo
from Products.ZenModel.Location import manage_addLocation
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.utils import unbrain


class DeviceFacadeTest(ZuulFacadeTestCase):

    def afterSetUp(self):
        super(DeviceFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('device', self.dmd)
        # Un-jobify jobby methods
        self.facade.moveDevices = self.facade._moveDevices
        self.facade.deleteDevices = self.facade._deleteDevices

    def test_interfaces(self):
        verifyClass(IDeviceInfo, DeviceInfo)

    def testDeleteOrganizerRemovesDevices(self):
        """When we delete an organizer all the devices assigned to it should not
        still have a relationship to it in the catalog
        """
        # Create Organizer
        organizer = self.facade.addOrganizer("/zport/dmd/Groups", 'testOrganizer')
        organizer_path = organizer.uid

        catalog = IModelCatalogTool(self.dmd)

        # Add some devices to it (use createInstance to create a device)
        devices = self.dmd.Devices
        test_device = devices.createInstance('testDevice')
        self.facade.moveDevices(['/'.join(test_device.getPhysicalPath())], organizer_path)
        organizer = self.dmd.unrestrictedTraverse(organizer_path)

        # test we have added the device
        self.assertEqual(len(organizer.getDevices()), 1, "make sure we saved our device")
        deviceBrains = catalog.search(paths='/'.join(organizer.getPhysicalPath()))
        self.assertTrue(deviceBrains.total > 1, " At this point we should have the organizer and the device")

        # Delete the Organizer
        self.facade.deleteNode(organizer_path)

        # Get the devices directly from the path
        deviceBrains = catalog.search(paths='/'.join(organizer.getPhysicalPath()))
        self.assertEqual(deviceBrains.total, 0, " we should not have any devices at this point")

    def test_removeDeviceFromSingleGroup(self):
        red = self.facade.addOrganizer("/zport/dmd/Groups", 'Red')
        red_org = self.dmd.unrestrictedTraverse(red.uid)

        orange = self.facade.addOrganizer("/zport/dmd/Groups/Red", 'Orange')
        orange_org = self.dmd.unrestrictedTraverse(orange.uid)

        yellow = self.facade.addOrganizer("/zport/dmd/Groups/Red/Orange", 'Yellow')
        yellow_org = self.dmd.unrestrictedTraverse(yellow.uid)

        test_device = self.dmd.Devices.createInstance('testDevice')

        groupNames = []
        for x in (red_org, orange_org, yellow_org):
            groupNames.append(x.getOrganizerName())

        test_device.setGroups(groupNames)

        groups = test_device.groups()

        # verify all our groups are there before removing one
        self.assertTrue(red_org in groups)
        self.assertTrue(orange_org in groups)
        self.assertTrue(yellow_org in groups)

        # remove a group
        self.facade.removeDevices((test_device.getPrimaryUrlPath(), ), orange_org)

        groups = test_device.groups()

        # verify only the group we removed is gone
        self.assertTrue(red_org in groups)
        self.assertTrue(not orange_org in groups)
        self.assertTrue(yellow_org in groups)

    def test_removeDeviceFromSingleSystem(self):
        blue = self.facade.addOrganizer("/zport/dmd/Systems", 'Blue')
        blue_org = self.dmd.unrestrictedTraverse(blue.uid)

        green = self.facade.addOrganizer("/zport/dmd/Systems/Blue", 'Green')
        green_org = self.dmd.unrestrictedTraverse(green.uid)

        yellow = self.facade.addOrganizer("/zport/dmd/Systems/Blue/Green", 'Yellow')
        yellow_org = self.dmd.unrestrictedTraverse(yellow.uid)

        test_device = self.dmd.Devices.createInstance('testDevice')

        systemNames = []
        for x in (blue_org, green_org, yellow_org):
            systemNames.append(x.getOrganizerName())

        test_device.setSystems(systemNames)

        systems = test_device.systems()

        # verify all our systems are there before removing one
        self.assertTrue(blue_org in systems)
        self.assertTrue(green_org in systems)
        self.assertTrue(yellow_org in systems)

        # remove a system
        self.facade.removeDevices((test_device.getPrimaryUrlPath(), ), green_org)

        systems = test_device.systems()

        # verify only the group we removed is gone
        self.assertTrue(blue_org in systems)
        self.assertTrue(not green_org in systems)
        self.assertTrue(yellow_org in systems)

    def test_deviceSearchParams(self):
        """
        Search for something we defniitely do not have
        in the global catalog indexes
        """
        dev = self.dmd.Devices.createInstance('dev')
        manage_addLocation(self.dmd.Locations, "test1")
        dev.setLocation("/test1")
        notify(IndexingEvent(dev))
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", params=dict(location="test1"))
        self.assertEquals(1, results.total)

    def test_deviceSearchAndSortByProdState(self):
        devMaintenance = self.dmd.Devices.createInstance('devMaintenance')
        devMaintenance.setPerformanceMonitor('localhost')
        devMaintenance.setProdState(400)

        devProduction = self.dmd.Devices.createInstance('devProduction')
        devProduction.setPerformanceMonitor('localhost')
        devProduction.setProdState(1000)

        # Search by prod state
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", params=dict(productionState=[400]))
        self.assertEquals(1, results.total)
        self.assertEquals(iter(results).next().getObject().getProductionState(), 400)

        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", params=dict(productionState=[1000]))
        self.assertEquals(1, results.total)
        self.assertEquals(iter(results).next().getObject().getProductionState(), 1000)

        # Sort by prod state
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort='productionState')
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        self.assertEquals(resultIter.next().getObject().getProductionState(), 400)
        self.assertEquals(resultIter.next().getObject().getProductionState(), 1000)

        # Sort by prod state, descending order
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort='productionState', dir='DESC')
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        self.assertEquals(resultIter.next().getObject().getProductionState(), 1000)
        self.assertEquals(resultIter.next().getObject().getProductionState(), 400)

        # This test specifically verifies the fix for ZEN-26901 sorting by a non-indexed
        # field while filtering on productionState caused a ProdStateNotSetError.

        # sort by status (non-indexed) with productionState filter
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort='status', params=dict(productionState=[400, 1000]))
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        device = resultIter.next()
        self.assertEquals(device.getProductionState(), 400)
        self.assertEquals(device.getPerformanceServer().id, 'localhost')
        device = resultIter.next()
        self.assertEquals(device.getProductionState(), 1000)
        self.assertEquals(device.getPerformanceServer().id, 'localhost')

        # sort by name (indexed) with productionState filter
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort='name', params=dict(productionState=[400, 1000]))
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        device = resultIter.next()
        self.assertEquals(device.getObject().getProductionState(), 400)
        device = resultIter.next()
        self.assertEquals(device.getObject().getProductionState(), 1000)

        # This test specifically verifies the fix for ZEN-26901 sorting productionState
        # while filtering on an indexed field caused a ProdStateNotSetError.

        # sort by productionState with name (indexed) filter
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort="productionState", params=dict(name="dev"))
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        device = resultIter.next()
        self.assertEquals(device.getObject().getProductionState(), 400)
        self.assertEquals(device.getObject().getDeviceName(), 'devMaintenance')
        device = resultIter.next()
        self.assertEquals(device.getObject().getProductionState(), 1000)
        self.assertEquals(device.getObject().getDeviceName(), 'devProduction')

        # sort by productionState with collector (non-indexed) filter
        results = self.facade.getDeviceBrains(uid="/zport/dmd/Devices", sort='productionState', params=dict(collector="local"))
        resultIter = iter(results)
        self.assertEquals(2, results.total)
        device = unbrain(resultIter.next())
        self.assertEquals(device.getProductionState(), 400)
        self.assertEquals(device.getPerformanceServer().id, 'localhost')
        device = unbrain(resultIter.next())
        self.assertEquals(device.getProductionState(), 1000)
        self.assertEquals(device.getPerformanceServer().id, 'localhost')

    def test_setProductionState(self):
        dev = self.dmd.Devices.createInstance('dev')
        dev2 = self.dmd.Devices.createInstance('dev2')

        self.assertEqual(dev.getProductionState(), 1000)
        self.assertEqual(dev2.getProductionState(), 1000)

        self.facade.setProductionState((dev.getPrimaryUrlPath(),
                                        dev2.getPrimaryUrlPath()), 500)

        self.assertEqual(dev.getProductionState(), 500)
        self.assertEqual(dev2.getProductionState(), 500)

def test_suite():
    return unittest.TestSuite((unittest.makeSuite(DeviceFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
