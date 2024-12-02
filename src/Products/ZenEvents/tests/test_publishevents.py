##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.interface import implements
from Products.ZenMessaging.queuemessaging.adapters import EventProtobuf as Serializer
from Products.ZenMessaging.queuemessaging.publisher import EventPublisher, getModelChangePublisher, DummyQueuePublisher
from zenoss.protocols.protobufs.zep_pb2 import Event
from Products.ZenEvents.Event import buildEventFromDict

class TestPublishEvents(BaseTestCase):

    def afterSetUp(self):
        super(TestPublishEvents, self).afterSetUp()
        self.publisher = getModelChangePublisher()
        # create a dummy device
        self.device = self.dmd.Devices.createInstance('testDevice')
        self.publisher.publishAdd(self.device)


    def beforeTearDown(self):
        self.publisher = None
        self.device = None
        super(TestPublishEvents, self).beforeTearDown()

    def _createDummyEvent(self):
        """
        creates a dummy event
        """
        device = self.device
        eventData = dict(
            device= device.id,
            component= "",
            eventClass= "/Status/Snmp",
            eventKey="pepe1",
            summary= "2.5 second timeout connecting to device 10.87.209.147",
            message= "2.5 second timeout connecting to device 10.87.209.147",
            severity= 4,
            eventState= 0,
            eventClassKey= "testEventClassKey",
            eventGroup= "SnmpTest",
            stateChange= "2010-09-24 07:12:19",
            count= 1,
            prodState= 1000,
            suppid= "",
            manager= "localhost",
            agent= "zenperfsnmp",
            DeviceClass= "/Server/Darwin",
            Location= "testLocation",
            Systems= "System1|System2",
            DeviceGroups= "Group1|Group2",
            ipAddress= "10.87.209.147",
            facility= "unknown",
            priority= 1,
            ownerid = "admin",
            ntevid= 0,
            evid="123456789",
            DevicePriority= 3,
            monitor= "localhost")
        return buildEventFromDict(eventData)

    def testAdaptingEventtoProtobuf(self):
        # setup event and device
        device = self.device
        event = self._createDummyEvent()
        event.foo = "bar"
        proto = Event()
        serializer = Serializer(event)

        # fill the protobuf
        proto = serializer.fill(proto)

        # check the results
        self.assertEqual(proto.agent, event.agent)
        self.assertEqual(proto.event_key, event.eventKey)

        # make sure the actor was set
        self.assertEqual(proto.actor.element_identifier, device.id)
        # make sure we have at least one detail
        self.assertTrue(len(proto.details) >= 1)
        reverse_event_field_map = {
            "zenoss.device.ip_address": "ipAddress"
        }
        for detail in proto.details:
            try:
                expected = getattr(event, detail.name)
            except AttributeError:
                expected = getattr(event, reverse_event_field_map[detail.name])
            self.assertEqual(detail.value[0], expected)
        # the new severity value
        self.assertEqual(proto.severity, 4)

    def testFacilityConversion(self):
        event = self._createDummyEvent()
        proto = Event()
        serializer = Serializer(event)
        event.facility = "1"
        # fill the protobuf
        proto = serializer.fill(proto)
        # should have converted to an int
        self.assertEqual(proto.syslog_facility, 1)
        self.assertEqual(proto.event_class_key, event.eventClassKey)

    def testUsingPublisher(self):
        event = self._createDummyEvent()
        publisher = EventPublisher()
        EventPublisher._publisher = DummyQueuePublisher()
        publisher.publish(event)
        EventPublisher._publisher = None

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPublishEvents))
    return suite
