##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import transaction
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher
from Products.ZenMessaging.queuemessaging.publisher import getModelChangePublisher, PublishSynchronizer, DummyQueuePublisher
from zenoss.protocols.protobufs.modelevents_pb2 import ModelEventList
from Products.ZenModel.DeviceClass import DeviceClass


log = logging.getLogger("zen.dynamicservices")

class TestPublishModelChanges(BaseTestCase):

    def afterSetUp(self):
        super(TestPublishModelChanges, self).afterSetUp()
        
        self.publisher = getModelChangePublisher()
        from zope.component import getGlobalSiteManager
        # register the component
        gsm = getGlobalSiteManager()
        queue = DummyQueuePublisher()
        gsm.registerUtility(queue, IQueuePublisher)
        self.queue = queue
        # create a dummy device
        self.device = self.dmd.Devices.createInstance('testDevice')
        self.publisher.publishAdd(self.device)


    def beforeTearDown(self):
        super(TestPublishModelChanges, self).beforeTearDown()
        self.publisher = None
        self.device = None
        self.queue = None

    def testObjectNotifyEvent(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.publishModified(self.device)
        self.assertEqual(len(self.publisher.events), 1)

    def testObjectRemovedEvent(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.publishRemove(self.device)
        self.assertEqual(len(self.publisher.events), 1)

    def testAddToOrganizer(self):
        self.publisher._eventList = ModelEventList()
        self.publisher.addToOrganizer(self.device, self.dmd.Devices)
        self.publisher.removeFromOrganizer(self.device, self.dmd.Devices)
        self.assertEqual(len(self.publisher.events), 3)

    def testDeviceClassMove(self):
        """
        This test is a little tricky. When we move device classes
        an ADD, REMOVE, and MOVE events are all fired.
        We need to coordinate those to make sure that only
        one MOVE event is sent
        """
        deviceClass = self.device.deviceClass()
        target = DeviceClass('pepe')
        deviceClass._setObject(target.id, target)
        # clear the event list
        self.publisher._eventList = ModelEventList()

        device = self.device

        # device
        self.publisher.publishRemove(device)
        self.publisher.publishAdd(device)

        # make sure only 1 event is fired
        self.publisher.moveObject(device, deviceClass, target)
        sync = PublishSynchronizer()
        events = sync.correlateEvents(self.publisher.events)
        self.assertEqual(len(events), 1, "should only be one move event")

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPublishModelChanges))
    return suite
