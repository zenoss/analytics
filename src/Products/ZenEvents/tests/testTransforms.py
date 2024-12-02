##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2011, 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from mock import patch

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.zeneventd import EventPipelineProcessor
from Products.ZenEvents.events2.processing import DropEvent
from Products.ZenEvents.events2.proxy import EventProxy
from zenoss.protocols.protobufs.zep_pb2 import (
    Event,
    STATUS_CLOSED,
    STATUS_SUPPRESSED,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_CLEAR,
)
from zenoss.protocols.protobufs.model_pb2 import DEVICE, COMPONENT
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

perfFilesystemTransform = """
if device and evt.eventKey:
    for f in device.os.filesystems():
        if f.name() != evt.component and f.id != evt.component: continue

        # Extract the used blocks from the event's message
        import re
        m = re.search(
            "threshold of [^:]+: current value ([\d\.]+)", evt.message
        )
        if not m: continue
    
        # Get the total blocks from the model. Adjust by specified offset.
        totalBlocks = f.totalBlocks * getattr(
            device, "zFileSystemSizeOffset", 1.0
        )
        totalBytes = totalBlocks * f.blockSize
        usedBytes = None
        
        currentValue = float(m.groups()[0])
        if 'usedBlocks' in evt.eventKey:
            usedBytes = currentValue * f.blockSize
        elif 'FreeMegabytes' in evt.eventKey:
            usedBytes = totalBytes - (currentValue * 1048576)
        else:
            continue
        
        # Calculate the used percent and amount free.
        usedBlocks = float(m.groups()[0])
        p = (usedBytes / totalBytes) * 100
        from Products.ZenUtils.Utils import convToUnits
        free = convToUnits(totalBytes - usedBytes)

        # Make a nicer summary
        evt.summary = (
            "disk space threshold: %3.1f%% used (%s free)"
        ) % (p, free)
        evt.message = evt.summary
        break
"""

PATH = {"src": "Products.ZenEvents.zeneventd"}

class TestTransforms(BaseTestCase):
    def afterSetUp(self):
        super(TestTransforms, self).afterSetUp()

        class MockConnection(object):
            def sync(self):
                pass

        self.dmd._p_jar = MockConnection()
        self.dmd.Events.createOrganizer("/Perf/Filesystem")
        self.dmd.Events.Perf.Filesystem.transform = perfFilesystemTransform

        self.MetricReporter_patcher = patch(
            "{src}.MetricReporter".format(**PATH)
        )
        self.MetricReporter_mock = self.MetricReporter_patcher.start()
        self.addCleanup(self.MetricReporter_patcher.stop)

        self.processor = EventPipelineProcessor(self.dmd)
        self.processor.reporter.stop()

    def _processEvent(self, event):
        # Don't return a sub-message from a C++ protobuf class - can
        # crash as the parent is GC'd.
        return self.processor.processMessage(event)

    def testPerfFileSystemTransformPerfFS(self):
        """
        Test to make sure that the standard transform on the /Perf/Filesystem
        event class works properly for stock performance templates.
        """

        # Test an example event from a standard SNMP device.
        device = self.dmd.Devices.createInstance("snmpdevice")
        device.os.addFileSystem("/", False)
        fs = device.os.filesystems()[0]
        fs.mount = "/"
        fs.blockSize = 4096
        fs.totalBlocks = 29221228

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.name()
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = "usedBlocks_usedBlocks|high disk usage"
        event.event_class = "/Perf/Filesystem"
        event.summary = (
            "threshold of high disk usage exceeded: current value 23476882.00"
        )

        processed = self._processEvent(event)
        self.assertEquals(
            processed.event.summary,
            "disk space threshold: 80.3% used (21.9GB free)",
        )

    def testPerfFileSystemTransformPerfmon(self):
        # Test an example event from a standard Perfmon device.
        device = self.dmd.Devices.createInstance("perfmondevice")
        device.os.addFileSystem("C", False)
        fs = device.os.filesystems()[0]
        fs.mount = " Label:C: Serial Number: 1471843B"
        fs.blockSize = 8192
        fs.totalBlocks = 1047233

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.name()
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = "FreeMegabytes_FreeMegabytes"
        event.event_class = "/Perf/Filesystem"
        event.summary = (
            "threshold of low disk space not met: current value 4156.00"
        )

        processed = self._processEvent(event)
        self.assertEquals(
            processed.event.summary,
            "disk space threshold: 49.2% used (4.1GB free)",
        )

    def testPerfFileSystemTransformSSH(self):
        # Test an example event from a standard SSH device.
        device = self.dmd.Devices.createInstance("sshdevice")
        device.os.addFileSystem("/", False)
        fs = device.os.filesystems()[0]
        fs.mount = "/"
        fs.blockSize = 1024
        fs.totalBlocks = 149496116

        event = Event()
        event.actor.element_identifier = device.id
        event.actor.element_type_id = DEVICE
        event.actor.element_sub_identifier = fs.id
        event.actor.element_sub_type_id = COMPONENT
        event.severity = SEVERITY_WARNING
        event.event_key = "disk|disk_usedBlocks|Free Space 90 Percent"
        event.event_class = "/Perf/Filesystem"
        event.summary = (
            "threshold of Free Space 90 Percent exceeded: "
            "current value 73400348.00"
        )

        processed = self._processEvent(event)
        self.assertEquals(
            processed.event.summary,
            "disk space threshold: 49.1% used (72.6GB free)",
        )

    def testActorReidentificationFromEventClassKeyTransform(self):
        """
        Verify that changing the device in a transform properly reidentifies
        the device when matching an event by eventClassKey.
        """
        device_a = self.dmd.Devices.createInstance("transform_device_a")

        # Related: ZEN-1419
        # If you change a device from within a transform like so:
        #
        #   evt.device = 'my_new_device'
        #
        # The processing pipeline will recognize this and re-run the
        # identification pipes. Before it re-runs these pipes though, it will
        # clear several properties related to the device, one of which is the
        # device/element UUID. During the Identification pipe, if the UUID
        # is missing, it will try one last time to lookup the element
        # using the identifier and the ip address. If we do not set an
        # ip address here, this test will not be completely testing the
        # reidentification logic.
        device_a.setManageIp("192.168.100.100")

        device_b = self.dmd.Devices.createInstance("transform_device_b")

        _transform_key = "transform_test_key"
        _transform = """
evt.device = '%s'
        """
        self.dmd.Events.createOrganizer("/transform_test")
        self.dmd.Events.transform_test.transform = _transform % device_b.id

        # the organizer above contains the transform, no create an instance
        # that actually contains the event class key.
        self.dmd.Events.transform_test.createInstance(_transform_key)

        event = Event()
        event.actor.element_identifier = device_a.id
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_WARNING
        event.summary = "Testing transforms."

        detail = event.details.add()
        detail.name = EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY
        detail.value.append(device_a.getManageIp())

        # Match the transform by event_class_key
        event.event_class_key = _transform_key
        processed = self._processEvent(event)

        self.assertEquals(
            device_b.id, processed.event.actor.element_identifier
        )
        self.assertEquals(
            IGlobalIdentifier(device_b).getGUID(),
            processed.event.actor.element_uuid,
        )

    def testActorReidentificationFromEventClassKeyTransformWithComponent(self):
        """
        Verify that changing the device in a transform properly reidentifies
        the device when matching an event by eventClassKey.
        """

        devA = self.dmd.Devices.createInstance("transform_device_a")
        devA.os.addFileSystem("component", False)
        devA.setManageIp("192.168.100.100")

        devB = self.dmd.Devices.createInstance("transform_device_b")
        devB.os.addFileSystem("component", False)
        devB.setManageIp("192.168.100.101")

        _transform_key = "transform_test_key"
        self.dmd.Events.createOrganizer("/transform_test")
        self.dmd.Events.transform_test.transform = (
            "evt.device = '%s'" % devB.id
        )
        self.dmd.Events.transform_test.createInstance(_transform_key)

        event = Event()
        event.actor.element_identifier = devA.id
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_WARNING
        event.summary = "Testing transforms on component."
        event.actor.element_sub_type_id = COMPONENT
        event.actor.element_sub_identifier = devA.getDeviceComponents()[0].id

        detail = event.details.add()
        detail.name = EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY
        detail.value.append(devA.getManageIp())

        # Match the transform by event_class_key
        event.event_class_key = _transform_key
        processed = self._processEvent(event)
        self.assertEquals(
            IGlobalIdentifier(devB.getDeviceComponents()[0]).getGUID(),
            processed.event.actor.element_sub_uuid,
        )

    def testIntSeverityTransform(self):
        """
        Transform the event severity to a string and see if it evaluates.
        """
        transform = 'evt.severity="0"; evt.summary="transformed"'
        self.dmd.Events.createOrganizer("/Perf/Filesystem")
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = "localhost"
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = "/Perf/Filesystem"
        event.summary = "bad thingy"

        processed = self._processEvent(event)
        self.assertEqual(SEVERITY_CLEAR, processed.event.severity)
        self.assertEqual("transformed", processed.event.summary)
        self.assert_(isinstance(processed.event.severity, int))

    def testActionDropped(self):
        transform = 'evt._action="drop"'
        self.dmd.Events.createOrganizer("/Perf/Filesystem")
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = "localhost"
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = "/Perf/Filesystem"
        event.summary = "should be dropped"

        self.assertRaises(DropEvent, self._processEvent, event)

    def testActionHistory(self):
        transform = 'evt._action="history"'
        self.dmd.Events.createOrganizer("/Perf/Filesystem")
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = "localhost"
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.event_class = "/Perf/Filesystem"
        event.summary = "should be closed"

        processed = self._processEvent(event)
        self.assertEqual(STATUS_CLOSED, processed.event.status)

    def testActionStatusDoesntChangeSuppressed(self):
        """
        If an event comes in as suppressed and the _action says to keep it in
        _status (the default), make sure that we don't accidentally change
        the status of the event back to STATUS_NEW.
        """
        transform = 'evt._action="status"'
        self.dmd.Events.createOrganizer("/Perf/Filesystem")
        self.dmd.Events.Perf.Filesystem.transform = transform

        event = Event()
        event.actor.element_identifier = "localhost"
        event.actor.element_type_id = DEVICE
        event.severity = SEVERITY_ERROR
        event.status = STATUS_SUPPRESSED
        event.event_class = "/Perf/Filesystem"
        event.summary = "should be suppressed"

        processed = self._processEvent(event)
        self.assertEqual(STATUS_SUPPRESSED, processed.event.status)


# def test_suite():
#     from unittest import TestSuite, makeSuite
# 
#     suite = TestSuite()
#     suite.addTest(makeSuite(testTransforms))
#     return suite
