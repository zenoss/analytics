##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os

from twisted.internet.defer import failure
from zope.interface import implementer
from zope.component import getGlobalSiteManager

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenHub.interfaces import (
    ICollectorEventTransformer,
    TRANSFORM_DROP,
)
from Products.ZenHub.PBDaemon import PBDaemon
from Products.ZenHub.events.queue.manager import EventQueueManager
from Products.ZenHub.events.queue.deduping import DeDupingEventQueue
from Products.ZenHub.events.queue.deque import DequeEventQueue
from Products.ZenHub.events.queue.fingerprint import (
    DefaultFingerprintGenerator,
)

_TEST_EVENT = {
    "device": "device1",
    "component": "component1",
    "eventClass": "/MyEventClass",
    "eventKey": "MyEventKey",
    "severity": 5,
    "summary": "My summary",
}

log = logging.getLogger("zen.testPBDaemon")


def createTestEvent(**kwargs):
    evt = _TEST_EVENT.copy()
    evt.update(kwargs)
    return evt


class BaseEventQueueTest(BaseTestCase):
    def __init__(self, queue_type, maxlen, *args, **kwargs):
        super(BaseEventQueueTest, self).__init__(*args, **kwargs)
        self.queue_type = queue_type
        self.maxlen = maxlen

    def afterSetUp(self):
        super(BaseEventQueueTest, self).afterSetUp()
        self.queue = self.queue_type(self.maxlen)

    def testPopLeft(self):
        self.queue.append(createTestEvent(device="device1"))
        self.queue.append(createTestEvent(device="device2"))
        self.assertEquals(2, len(self.queue))
        evt = self.queue.popleft()
        self.assertEquals("device1", evt["device"])
        self.assertEquals(1, len(self.queue))
        evt = self.queue.popleft()
        self.assertEquals("device2", evt["device"])
        self.assertEquals(0, len(self.queue))
        self.assertRaises(IndexError, self.queue.popleft)

    def testExtendLeft(self):
        self.queue.extendleft([])
        self.assertEquals(0, len(self.queue))
        evt1 = createTestEvent(device="device1")
        self.queue.append(evt1)
        evt2 = createTestEvent(device="device2")
        self.queue.append(evt2)
        self.assertEquals(2, len(self.queue))

        additional_events = [
            createTestEvent(device="device_00%d" % i) for i in range(25)
        ]
        discarded = self.queue.extendleft(additional_events)
        self.assertEquals(10, len(self.queue))
        queued = list(self.queue)
        self.assertEquals(additional_events[17:], queued[:8])
        self.assertEquals(evt1, queued[-2])
        self.assertEquals(evt2, queued[-1])
        self.assertEquals(additional_events[:17], discarded)


class TestDeDupingEventQueue(BaseEventQueueTest):
    def __init__(self, *args, **kwargs):
        super(TestDeDupingEventQueue, self).__init__(
            DeDupingEventQueue, 10, *args, **kwargs
        )

    def testDeDuping(self):
        for _ in range(100):
            self.queue.append(createTestEvent(mydetail="detailvalue"))
        self.assertEquals(1, len(self.queue))
        queued = list(self.queue)
        self.assertEquals(100, queued[0]["count"])
        # Ensure that the most recent event is on the queue
        self.assertEquals("detailvalue", queued[0]["mydetail"])

        evt_unique = createTestEvent(component="component2")
        self.queue.append(evt_unique.copy())
        self.queue.append(evt_unique.copy())
        self.assertEquals(2, len(self.queue))
        queued = list(self.queue)
        self.assertEquals(100, queued[0]["count"])
        self.assertEquals(2, queued[1]["count"])

    def testExtendLeftDedup(self):
        self.queue.append(createTestEvent(device="dev1"))
        self.queue.append(createTestEvent(device="dev2"))
        self.queue.append(createTestEvent(device="dev4"))
        self.assertEquals(3, len(self.queue))
        events = []
        events.append(self.queue.popleft())
        events.append(self.queue.popleft())
        events.append(self.queue.popleft())
        self.assertEquals(0, len(self.queue))
        self.queue.append(createTestEvent(device="dev1"))
        self.queue.append(createTestEvent(device="dev2"))
        self.queue.append(createTestEvent(device="dev3"))
        self.assertEquals(3, len(self.queue))
        self.queue.extendleft(events)
        queued = list(self.queue)
        self.assertEquals(4, len(queued))
        self.assertEquals("dev4", queued[0]["device"])
        self.assertEquals(0, queued[0].get("count", 0))
        self.assertEquals("dev1", queued[1]["device"])
        self.assertEquals(2, queued[1]["count"])
        self.assertEquals("dev2", queued[2]["device"])
        self.assertEquals(2, queued[2]["count"])
        self.assertEquals("dev3", queued[3]["device"])
        self.assertEquals(0, queued[3].get("count", 0))


class TestDequeEventQueue(BaseEventQueueTest):
    def __init__(self, *args, **kwargs):
        super(TestDequeEventQueue, self).__init__(
            DequeEventQueue, 10, *args, **kwargs
        )


class TestEventQueueManager(BaseTestCase):
    def afterSetUp(self):
        super(TestEventQueueManager, self).afterSetUp()
        self.gsm = getGlobalSiteManager()

    def createOptions(
        self,
        deduplicate_events=True,
        maxqueuelen=5000,
        allowduplicateclears=False,
        duplicateclearinterval=0,
        eventflushchunksize=50,
    ):
        class MockOptions(object):
            pass

        options = MockOptions()
        options.deduplicate_events = deduplicate_events
        options.maxqueuelen = maxqueuelen
        options.allowduplicateclears = allowduplicateclears
        options.duplicateclearinterval = duplicateclearinterval
        options.eventflushchunksize = eventflushchunksize
        return options

    def testAddEventDroppedTransform(self):
        @implementer(ICollectorEventTransformer)
        class DroppingTransformer(object):
            def __init__(self):
                self.num_dropped = 0

            def transform(self, event):
                self.num_dropped += 1
                return TRANSFORM_DROP

        transformer = DroppingTransformer()
        self.gsm.registerUtility(transformer)
        try:
            eqm = EventQueueManager(self.createOptions(), log)
            for _ in range(5):
                eqm.addEvent(createTestEvent())
        finally:
            self.gsm.unregisterUtility(transformer)

        self.assertEquals(5, transformer.num_dropped)

    def testDiscarded(self):
        eqm = EventQueueManager(self.createOptions(maxqueuelen=1), log)
        evt1 = createTestEvent(device="foo")
        eqm.addEvent(evt1)
        self.assertEquals(0, eqm.discarded_events)
        evt2 = createTestEvent(device="foo2")
        eqm.addEvent(evt2)
        self.assertEquals(1, eqm.discarded_events)
        self.assertEquals(list(eqm.event_queue), [evt2])

    def testNoDuplicateClears(self):
        eqm = EventQueueManager(self.createOptions(), log)
        for _ in range(5):
            eqm.addEvent(createTestEvent(severity=0))
        self.assertEquals(1, len(eqm.event_queue))
        sent_events = []
        eqm.sendEvents(lambda evts: sent_events.extend(evts))

        for _ in range(5):
            eqm.addEvent(createTestEvent(severity=0))
        self.assertEquals(0, len(eqm.event_queue))

    def testDuplicateClears(self):
        opts = self.createOptions(allowduplicateclears=True)
        eqm = EventQueueManager(opts, log)
        sent_events = []

        def send_events(evts):
            sent_events.extend(evts)

        for _ in range(5):
            eqm.addEvent(createTestEvent(severity=0))
            eqm.sendEvents(send_events)
        self.assertEquals(5, len(sent_events))

    def testDuplicateClearInterval(self):
        opts = self.createOptions(
            allowduplicateclears=True, duplicateclearinterval=5
        )
        sent_events = []

        def send_events(evts):
            sent_events.extend(evts)

        eqm = EventQueueManager(opts, log)
        for _ in range(10):
            eqm.addEvent(createTestEvent(severity=0))
            eqm.sendEvents(send_events)
        self.assertEquals(2, len(sent_events))

    def testDiscardedClearHandling(self):
        opts = self.createOptions(maxqueuelen=1)
        eqm = EventQueueManager(opts, log)
        # Send a clear which is later discarded
        eqm.addEvent(createTestEvent(severity=0))
        # Send an event that wipes it out
        eqm.addEvent(createTestEvent())
        self.assertEquals(1, eqm.discarded_events)
        # Send events
        eqm.sendEvents(lambda evts: None)
        # Send the clear again
        clearevt = createTestEvent(severity=0)
        eqm.addEvent(clearevt)
        sent_events = []

        def send_events(evts):
            sent_events.extend(evts)

        eqm.sendEvents(send_events)
        self.assertEquals([clearevt], sent_events)

    def testEventChunking(self):
        opts = self.createOptions(eventflushchunksize=5)
        eqm = EventQueueManager(opts, log)
        events = []
        for i in range(10):
            events.append(createTestEvent(device="dev%d" % i))
            eqm.addEvent(events[-1])
        perf_events = []
        for i in range(10):
            perf_events.append(createTestEvent(device="perfdev%d" % i))
            eqm.addPerformanceEvent(perf_events[-1])
        heartbeat_events = [createTestEvent(eventClass="/Heartbeat")]
        eqm.addHeartbeatEvent(heartbeat_events[-1])
        sent_event_chunks = []

        def send_events(events):
            sent_event_chunks.append(events)

        eqm.sendEvents(send_events)
        self.assertEquals(5, len(sent_event_chunks))
        # First chunk should be heartbeat + 4 perf
        self.assertEquals(
            heartbeat_events + perf_events[:4], sent_event_chunks[0]
        )
        # Second chunk should be 5 perf
        self.assertEquals(perf_events[4:9], sent_event_chunks[1])
        # Third chunk should be 1 perf + 4 events
        self.assertEquals(perf_events[9:] + events[0:4], sent_event_chunks[2])
        # Fourth chunk should be 5 events
        self.assertEquals(events[4:9], sent_event_chunks[3])
        # Fifth chunk should be 1 event
        self.assertEquals(events[9:], sent_event_chunks[4])

    def testRestoreEvents(self):
        opts = self.createOptions(eventflushchunksize=5)
        eqm = EventQueueManager(opts, log)
        events = []
        for i in range(10):
            events.append(createTestEvent(device="dev%d" % i))
            eqm.addEvent(events[-1])
        perf_events = []
        for i in range(7):
            perf_events.append(createTestEvent(device="perfdev%d" % i))
            eqm.addPerformanceEvent(perf_events[-1])

        sent_event_chunks = []

        def send_events(events):
            # Send an exception on the second batch
            if len(sent_event_chunks) == 1:
                raise Exception("Test Exception")
            sent_event_chunks.append(events)

        results = []

        def finished_events(result):
            results.append(result)

        d = eqm.sendEvents(send_events)
        d.addBoth(finished_events)

        # Verify the first chunk was sent
        self.assertEquals(1, len(results))
        self.assertTrue(isinstance(results[0], failure.Failure))
        self.assertEquals(1, len(sent_event_chunks))
        self.assertEquals(sent_event_chunks[0], perf_events[:5])
        # Verify the second chunk (which threw an exception) was added back to
        # queues.
        self.assertEquals(perf_events[5:], list(eqm.perf_event_queue))
        self.assertEquals(events, list(eqm.event_queue))

    def testRestoreEventsDiscarded(self):
        opts = self.createOptions(eventflushchunksize=5, maxqueuelen=10)
        eqm = EventQueueManager(opts, log)
        events = []
        for i in range(10):
            if i == 0:
                events.append(createTestEvent(device="dev%d" % i, severity=0))
            else:
                events.append(createTestEvent(device="dev%d" % i))
            eqm.addEvent(events[-1])

        def send_events(ignored_events):
            # Add 3 new events to the queue (while sending)
            for i in range(3):
                events.append(createTestEvent(device="dev%d" % (10 + i)))
                eqm.addEvent(events[-1])
            raise Exception("Failed on first send.")

        results = []

        def finished_events(result):
            results.append(result)

        d = eqm.sendEvents(send_events)
        d.addBoth(finished_events)

        self.assertEquals(1, len(results))
        self.assertTrue(isinstance(results[0], failure.Failure))
        # 3 earliest events should be discarded
        self.assertEquals(3, eqm.discarded_events)
        self.assertEquals(10, len(eqm.event_queue))
        self.assertEquals(events[3:], list(eqm.event_queue))

        # The state of the clear event should be removed, so it should be
        # allowed to be sent again.
        sent_events = []
        eqm.addEvent(events[0])
        eqm.sendEvents(lambda evts: sent_events.extend(evts))
        self.assertTrue(events[0] in sent_events)


class TestDefaultFingerprintGenerator(BaseTestCase):
    def afterSetUp(self):
        super(TestDefaultFingerprintGenerator, self).afterSetUp()
        self.generator = DefaultFingerprintGenerator()

    def testGenerate(self):
        evt = createTestEvent()
        self.assertEquals(
            "65e9075c8b854688217c45471bb837ede3157d53",
            self.generator.generate(evt),
        )
        del evt["eventKey"]
        self.assertEquals(
            "4f39c417bdee2731336bf6a9f22c89fbe4d987b0",
            self.generator.generate(evt),
        )

    def testDeDupingSensitivity(self):
        evt = createTestEvent(device="dev1")
        # changing an attribute should change fingerprint
        for attr in "device component eventKey summary eventClass".split():
            fp1 = self.generator.generate(evt)
            evt[attr] += "***"
            fp2 = self.generator.generate(evt)
            self.assertNotEquals(
                fp1, fp2, "changing %s not detected in fingerprint" % attr
            )

        # adding a new attribute should change fingerprint
        fp1 = self.generator.generate(evt)
        evt["new_attribute"] = "zillion"
        fp2 = self.generator.generate(evt)
        self.assertNotEquals(
            fp1, fp2, "adding new key not detected in fingerprint"
        )

        # changing these attributes should NOT change fingerprint
        for attr in "rcvtime firstTime lastTime".split():
            evt[attr] = "qwertyuiop"
            fp1 = self.generator.generate(evt)
            evt[attr] += "***"
            fp2 = self.generator.generate(evt)
            self.assertEquals(
                fp1, fp2, "changing %s not ignored in fingerprint" % attr
            )


class Publisher(object):
    def __init__(self):
        self.queue = []

    def put(self, *args):
        self.queue.append(args)


class TestMetricWriter(BaseTestCase):
    def setUp(self):
        os.environ["CONTROLPLANE"] = "0"
        self.publisher = Publisher()
        self.daemon = PBDaemon(publisher=self.publisher)
        self.metric_writer = self.daemon.metricWriter()

    def testWriteMetric(self):
        metric = ["name", 0.0, "now", {}]
        self.metric_writer.write_metric(*metric)
        self.assertEquals([tuple(metric)], self.publisher.queue)


class TestInternalMetricWriter(BaseTestCase):
    def setUp(self):
        os.environ["CONTROLPLANE"] = "1"
        self.publisher = Publisher()
        self.internal_publisher = Publisher()
        self.daemon = PBDaemon(
            publisher=self.publisher,
            internal_publisher=self.internal_publisher,
        )
        self.metric_writer = self.daemon.metricWriter()

    def testWriteInternalMetric(self):
        metric = ["name", 0.0, "now", {}]
        internal_metric = ["name", 0.0, "now", {"internal": True}]
        self.metric_writer.write_metric(*metric)
        self.metric_writer.write_metric(*internal_metric)
        self.assertEquals(
            [tuple(internal_metric)], self.internal_publisher.queue
        )
        self.assertEquals(
            [tuple(metric), tuple(internal_metric)], self.publisher.queue
        )

    def testInternalPublisherIsNone(self):
        self.daemon.setInternalPublisher(None)
        del os.environ["CONTROLPLANE_CONSUMER_URL"]
        self.assertIsNone(self.daemon.internalPublisher())

    def testInternalPublisherIsInstance(self):
        self.daemon.setInternalPublisher(None)
        os.environ["CONTROLPLANE_CONSUMER_URL"] = "http://localhost"
        publisher = self.daemon.internalPublisher()
        from Products.ZenHub.metricpublisher.publisher import HttpPostPublisher

        self.assertIsInstance(publisher, HttpPostPublisher)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestDeDupingEventQueue))
    suite.addTest(makeSuite(TestDequeEventQueue))
    suite.addTest(makeSuite(TestEventQueueManager))
    suite.addTest(makeSuite(TestDefaultFingerprintGenerator))
    suite.addTest(makeSuite(TestMetricWriter))
    suite.addTest(makeSuite(TestInternalMetricWriter))
    return suite
