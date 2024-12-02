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
    framework = None
    execfile(os.path.join(sys.path[0], 'framework.py'))

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.IpInterface import manage_addIpInterface
from Products.ZenModel.WinService import manage_addWinService
from Products.ZenUtils.FakeRequest import FakeRequest

from Products.Zuul.catalog.interfaces import IModelCatalogTool

LOCATION = '/TestLoc/MyLocation'
GROUP    = '/TestGrp/MyGroup'
SYSTEM   = '/TestSys/MySystem'
DEVCLASS = '/TestOrg/MyClass'
OTHERDEVCLASS = '/TestOrg/MyOtherClass'

MAC = '00:11:22:33:44:55'
IPADDR = '10.1.2.3/24'
NET = '10.1.2.0'

class TestPathIndexing(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestPathIndexing, self).afterSetUp()
        self.devcat = IModelCatalogTool(self.dmd.Devices).devices

        self.devclass = self.dmd.Devices.createOrganizer(DEVCLASS)
        self.loc = self.dmd.Locations.createOrganizer(LOCATION)
        self.grp = self.dmd.Groups.createOrganizer(GROUP)
        self.sys = self.dmd.Systems.createOrganizer(SYSTEM)

        # Control
        dummydev =  self.dmd.Devices.createInstance('dummydev')

        self.dev = self.devclass.createInstance('testdev')
        self.dev.setLocation(LOCATION)
        self.dev.setGroups((GROUP,))
        self.dev.setSystems((SYSTEM,))

    def testDeviceIndexOnCreation(self):
        for org in (self.loc, self.grp, self.sys, self.devclass):
            brains = list(self.devcat(paths='/'.join(org.getPrimaryPath())))
            self.assertEqual(len(brains), 1)
            self.assertEqual(brains[0].id, self.dev.id)
            self.assertEqual(brains[0].getObject(), self.dev)

    def testDeviceUnindexOnDeviceClassDelete(self):
        """
        Test deviceSearch is updated when a device class is moved. 
        """
        sourceOrg = self.dmd.Devices.createOrganizer('/Two/Three')
        dcmDevice = sourceOrg.createInstance('dcmDevice')
        self.dmd.Devices.Two._delObject('Three')
        brains = self.devcat()
        self.assertEqual(len(brains), 2) # dummydev and testdev

    def testDeviceUnindexOnRemoval(self):
        self.dev.setLocation('')
        self.dev.setGroups([])
        self.dev.setSystems([])

        for org in (self.loc, self.grp, self.sys):
            brains = self.devcat(paths='/'.join(org.getPrimaryPath()))
            self.assertEqual(len(brains), 0)

        self.dev.deleteDevice()
        brains = list(self.devcat(paths='/'.join(self.devclass.getPrimaryPath())))
        self.assertEqual(len(brains), 0)

    def testDeviceReindexOnMove(self):
        neworg = self.dmd.Devices.createOrganizer(DEVCLASS+'NEW')
        self.dmd.Devices.moveDevices(DEVCLASS+'NEW', self.dev.id)
        brains = list(self.devcat(paths='/'.join(neworg.getPrimaryPath())))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newloc = self.dmd.Locations.createOrganizer(LOCATION+'NEW')
        self.dev.setLocation(LOCATION+'NEW')
        brains = list(self.devcat(paths='/'.join(newloc.getPrimaryPath())))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newgrp = self.dmd.Groups.createOrganizer(GROUP+'NEW')
        self.dev.setGroups((GROUP+'NEW',))
        brains = list(self.devcat(paths='/'.join(newgrp.getPrimaryPath())))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)

        newsys = self.dmd.Systems.createOrganizer(SYSTEM + 'NEW')
        self.dev.setSystems((SYSTEM+'NEW',))
        brains = list(self.devcat(paths='/'.join(newsys.getPrimaryPath())))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, self.dev.id)
        self.assertEqual(brains[0].getObject(), self.dev)
    
    
    def testDeviceReindexOnDeviceClassMove(self):
        """
        Test deviceSearch is updated when a device class is moved. 
        """
        sourceOrg = self.dmd.Devices.createOrganizer('/Two/Three')
        dcmDevice = sourceOrg.createInstance('dcmDevice')
        destOrg = self.dmd.Devices.createOrganizer('/One')
        self.dmd.Devices.moveOrganizer('/Devices/One', ['Two'])
        brains = list(self.devcat(paths='/'.join(destOrg.getPrimaryPath())))
        self.assertEqual(len(brains), 1)
        self.assertEqual(brains[0].id, dcmDevice.id)
        self.assertEqual(brains[0].getObject(), dcmDevice)


    def testNonExistentDeviceInCatalog(self):
        """
        Verify that stale catalog entries won't result in tracebacks.
        """
        from zExceptions import NotFound
        d = self.dmd.Devices.createInstance('catTestDevice')

        from zope.event import notify
        from Products.Zuul.catalog.events import IndexingEvent
        notify(IndexingEvent(d))

        device_count = len(self.dmd.Devices.getSubDevices())
        self.dmd.Devices.devices._objects.pop('catTestDevice')
        try:
            self.assertEqual(len(self.dmd.Devices.getSubDevices()),
                device_count - 1)
        except (NotFound, KeyError, AttributeError) as ex:
            self.assertEqual(ex, None)


class TestComponentIndexing(ZenModelBaseTest):

    def afterSetUp(self):
        super(TestComponentIndexing, self).afterSetUp()
        self.model_catalog = IModelCatalogTool(self.dmd.Devices)
        self.layer2cat = self.model_catalog.layer2
        self.layer3cat = self.model_catalog.layer3

        self.devclass = self.dmd.Devices.createOrganizer(DEVCLASS)
        self.devclass2 = self.dmd.Devices.createOrganizer(DEVCLASS)

        # Control
        dummydev =  self.dmd.Devices.createInstance('dummydev')

        self.dev = self.devclass.createInstance('testdev')

        manage_addIpInterface(self.dev.os.interfaces, 'eth0', True)
        self.iface = self.dev.os.interfaces._getOb('eth0')
        self.iface._setPropValue('macaddress', MAC)
        self.iface.addIpAddress(IPADDR)
        self.ipaddress = self.iface.ipaddresses()[0]
        self.net = self.dmd.Networks.getNet(NET)
        
        manage_addWinService(self.dev.os.winservices,'wuauserv','test service')
        self.winService = self.dev.os.winservices._getOb('wuauserv')

    def getIdFromPath(self, path):
        """ return the last part of the path """
        _id = None
        if path:
            splitted = path.split('/')
            _id = splitted[-1] if splitted else None
        return _id

    def _checkEverything(self):
        for searchcriterion in (dict(macaddress=MAC),
                                dict(deviceId='/'.join(self.dev.getPrimaryPath())),
                                dict(interfaceId=self.iface.getPrimaryId())):
            brains = list(self.layer2cat(query=searchcriterion))
            self.assertEqual(len(brains), 1)
            brain = brains[0]
            self.assertEqual(brain.deviceId, '/'.join(self.dev.getPrimaryPath()))
            self.assertEqual(brain.interfaceId, self.iface.getPrimaryId())
            self.assertEqual(brain.macaddress, MAC)
            self.assertEqual(brain.lanId, None)
            self.assertEqual(brain.getObject(), self.iface)

        for searchcriterion in (dict(deviceId=self.dev.id),
                                dict(interfaceId=self.iface.id),
                                dict(ipAddressId=self.ipaddress.getPrimaryId()),
                                dict(networkId=self.net.getPrimaryId())
                               ):
            brains = list(self.layer3cat(query=searchcriterion))
            self.assertEqual(len(brains), 1)
            brain = brains[0]
            self.assertEqual(self.getIdFromPath(brain.deviceId), self.dev.id)
            self.assertEqual(self.getIdFromPath(brain.interfaceId), self.iface.id)
            self.assertEqual(brain.ipAddressId, self.ipaddress.getPrimaryId())
            self.assertEqual(brain.networkId, self.net.getPrimaryId())
            self.assertEqual(brain.getObject(), self.ipaddress)

    def testComponentIndexOnCreation(self):
        """
        Ensure that the layerN catalogs are updated when the device is created
        """
        self._checkEverything()

    def testComponentUnindexOnDeviceDeletion(self):
        """
        Ensure that the layerN catalogs are updated when the device is deleted
        """
        self.dev.deleteDevice()

        query = { "deviceId" : self.dev.getPrimaryId() }
        brains = list(self.layer2cat(query=query))
        self.assertEqual(len(brains), 0)

        query = { "deviceId" : self.dev.id }
        brains = list(self.layer3cat(query=query))
        self.assertEqual(len(brains), 0)

    def testComponentReindexOnDeviceMove(self):
        """
        Ensure that the layerN catalogs are updated when the device is moved
        """
        neworg = self.dmd.Devices.createOrganizer(DEVCLASS+'NEW')
        self.dmd.Devices.moveDevices(DEVCLASS+'NEW', self.dev.id)
        self._checkEverything()

    def testLayer3LinkUnindexOnNetworkDelete(self):
        """
        Ensure that the layerN catalogs are updated when the device is moved
        """
        # See that the link has been indexed properly
        brains = list(self.layer3cat( query = {"deviceId": self.dev.id} ))
        self.assertEqual(len(brains), 1)
        brains = list(self.layer3cat( query = {"networkId": self.net.getPrimaryId()} ))
        self.assertEqual(len(brains), 1)

        # Delete the network
        self.dmd.Networks._delObject(self.net.id)

        # See that the link has been unindexed
        brains = list(self.layer3cat( query = {"deviceId": self.dev.id} ))
        self.assertEqual(len(brains), 0)
        brains = list(self.layer3cat( query = {"networkId": self.net.getPrimaryId()} ))
        self.assertEqual(len(brains), 0)
        
    def testWinSerivceComponentReindexOnServiceClassZMonitorChange(self):
        """
        Ensure the WinServices in the componentSearch catalog are re-indexed 
        when saveZenProperties is called on the Service Class and zMonitor is 
        changed
        """
        svcClass = self.dmd.Services.WinService.serviceclasses._getOb(self.winService.id)
        
        winSvc = self.dev.getMonitoredComponents(type='WinService')
        #by default monitor is off; should find nothing
        self.assertFalse( winSvc )
        monitored = svcClass.zMonitor
        self.assertFalse( monitored )
        
        #fake request and turn zMonitor to true
        request = FakeRequest()
        request.form = {'zMonitor': True}
        kwargs = {'REQUEST': request}
        svcClass.saveZenProperties(**kwargs)
        
        #verify monitored flag changed and that component is now found
        monitored = svcClass.zMonitor
        self.assertTrue( monitored )
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        self.assertTrue ( winSvc2 )

        #test that changing zProperty directly does not affect catalog
        svcClass.setZenProperty('zMonitor', False)
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        #catalog will find component even though zMonitor is false
        #because index was not updated
        self.assertTrue ( winSvc2 )

    def testWinSerivceComponentReindexOnServiceOrganizerZMonitorChange(self):
        """
        Ensure the WinServices in the componentSearch catalog are re-indexed 
        when saveZenProperties is called on the Service Organizer and zMonitor
        is Changed 
        """

        svcOrg = self.dmd.Services
        winSvc = self.dev.getMonitoredComponents(type='WinService')
        #by default monitor is off; should find nothing
        self.assertFalse( winSvc )
        monitored = svcOrg.zMonitor
        self.assertFalse( monitored )
                
        #fake request and turn zMonitor to true
        request = FakeRequest()
        request.form = {'zMonitor': True}
        kwargs = {'REQUEST': request}
        svcOrg.saveZenProperties(**kwargs)
        
        #verify monitored flag changed and that component is now found
        monitored = svcOrg.zMonitor
        self.assertTrue( monitored )
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        self.assertTrue ( winSvc2 )

        #test that changing zProperty directly does not affect catalog
        svcOrg.setZenProperty('zMonitor', False)
        winSvc2 = self.dev.getMonitoredComponents(type='WinService')
        #catalog will find component even though zMonitor is false
        #because index was not updated
        self.assertTrue ( winSvc2 )
    
    def testComponentIndexOnDeviceClassMove(self):
        """
        Test to make sure that the componentSearch catalog is updated when
        an entire device class path is moved.
        """
        sourceOrg = self.dmd.Devices.createOrganizer('/Two/Three')
        dcmDevice = sourceOrg.createInstance('dcmDevice')
        dcmDevice.os.addFileSystem("/boot", False)
        destOrg = self.dmd.Devices.createOrganizer('/One')
        self.dmd.Devices.moveOrganizer('/Devices/One', ['Two'])
        components = dcmDevice.getMonitoredComponents(type='FileSystem')
        self.assertEqual(components[0].device().id, 'dcmDevice')


    def testNonExistentComponentInCatalog(self):
        """
        Verify that stale catalog entries won't result in tracebacks.
        """
        from zExceptions import NotFound
        d = self.dmd.Devices.createInstance('catTestDevice')
        d.index_object()
        d.os.addIpInterface('catTestComponent', True)
        c = d.os.interfaces._getOb('catTestComponent')
        c.index_object()
        component_count = len(d.getDeviceComponents())
        d.os.interfaces._objects.pop('catTestComponent')
        try:
            self.assertEqual(len(d.getDeviceComponents()), component_count - 1)
        except (NotFound, KeyError, AttributeError) as ex:
            self.assertEqual(ex, None)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPathIndexing))
    suite.addTest(makeSuite(TestComponentIndexing))
    return suite

if __name__=="__main__":
    framework()
