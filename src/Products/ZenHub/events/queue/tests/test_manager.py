import collections

from unittest import TestCase
from mock import MagicMock, Mock, create_autospec, call

# Breaks Test Isolation. Products/ZenHub/metricpublisher/utils.py:15
# ImportError: No module named eventlet
from Products.ZenHub.PBDaemon import Clear, defer
from ..deduping import DeDupingEventQueue
from ..manager import EventQueueManager, TRANSFORM_DROP, TRANSFORM_STOP

PATH = {"src": "Products.ZenHub.PBDaemon"}


class EventQueueManagerTest(TestCase):
    def setUp(t):
        options = Mock(
            name="options",
            spec_set=[
                "maxqueuelen",
                "deduplicate_events",
                "allowduplicateclears",
                "duplicateclearinterval",
                "eventflushchunksize",
            ],
        )
        options.deduplicate_events = True
        log = Mock(name="logger.log", spec_set=["debug", "warn"])

        t.eqm = EventQueueManager(options, log)
        t.eqm._initQueues()

    def test_initQueues(t):
        options = Mock(
            name="options", spec_set=["maxqueuelen", "deduplicate_events"]
        )
        options.deduplicate_events = True
        log = Mock(name="logger.log", spec_set=[])

        eqm = EventQueueManager(options, log)
        eqm._initQueues()

        t.assertIsInstance(eqm.event_queue, DeDupingEventQueue)
        t.assertEqual(eqm.event_queue.maxlen, options.maxqueuelen)
        t.assertIsInstance(eqm.perf_event_queue, DeDupingEventQueue)
        t.assertEqual(eqm.perf_event_queue.maxlen, options.maxqueuelen)
        t.assertIsInstance(eqm.heartbeat_event_queue, collections.deque)
        t.assertEqual(eqm.heartbeat_event_queue.maxlen, 1)

    def test_transformEvent(t):
        """a transformer mutates and returns an event"""

        def transform(event):
            event["transformed"] = True
            return event

        transformer = Mock(name="transformer", spec_set=["transform"])
        transformer.transform.side_effect = transform
        t.eqm.transformers = [transformer]

        event = {}
        ret = t.eqm._transformEvent(event)

        t.assertEqual(ret, event)
        t.assertEqual(event, {"transformed": True})

    def test_transformEvent_drop(t):
        """if a transformer returns TRANSFORM_DROP
        stop running the event through transformer, and return None
        """

        def transform_drop(event):
            return TRANSFORM_DROP

        def transform_bomb(event):
            0 / 0

        transformer = Mock(name="transformer", spec_set=["transform"])
        transformer.transform.side_effect = transform_drop
        transformer_2 = Mock(name="transformer", spec_set=["transform"])
        transformer_2.transform.side_effect = transform_bomb

        t.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = t.eqm._transformEvent(event)
        t.assertEqual(ret, None)

    def test_transformEvent_stop(t):
        """if a transformer returns TRANSFORM_STOP
        stop running the event through transformers, and return the event
        """

        def transform_drop(event):
            return TRANSFORM_STOP

        def transform_bomb(event):
            0 / 0

        transformer = Mock(name="transformer", spec_set=["transform"])
        transformer.transform.side_effect = transform_drop
        transformer_2 = Mock(name="transformer", spec_set=["transform"])
        transformer_2.transform.side_effect = transform_bomb

        t.eqm.transformers = [transformer, transformer_2]

        event = {}
        ret = t.eqm._transformEvent(event)
        t.assertIs(ret, event)

    def test_clearFingerprint(t):
        event = {k: k + "_v" for k in t.eqm.CLEAR_FINGERPRINT_FIELDS}

        ret = t.eqm._clearFingerprint(event)

        t.assertEqual(
            ret, ("device_v", "component_v", "eventKey_v", "eventClass_v")
        )

    def test__removeDiscardedEventFromClearState(t):
        """if the event's fingerprint is in clear_events_count
        decrement its value
        """
        t.eqm.options.allowduplicateclears = False
        t.eqm.options.duplicateclearinterval = 0

        discarded = {"severity": Clear}
        clear_fingerprint = t.eqm._clearFingerprint(discarded)
        t.eqm.clear_events_count[clear_fingerprint] = 3

        t.eqm._removeDiscardedEventFromClearState(discarded)

        t.assertEqual(t.eqm.clear_events_count[clear_fingerprint], 2)

    def test__addEvent(t):
        """remove the event from clear_events_count
        and append it to the queue
        """
        t.eqm.options.allowduplicateclears = False

        queue = MagicMock(name="queue", spec_set=["append", "__len__"])
        event = {}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: 3}

        t.eqm._addEvent(queue, event)

        t.assertNotIn(clear_fingerprint, t.eqm.clear_events_count)
        queue.append.assert_called_with(event)

    def test__addEvent_status_clear(t):
        t.eqm.options.allowduplicateclears = False
        t.eqm.options.duplicateclearinterval = 0

        queue = MagicMock(name="queue", spec_set=["append", "__len__"])
        event = {"severity": Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)

        t.eqm._addEvent(queue, event)

        t.assertEqual(t.eqm.clear_events_count[clear_fingerprint], 1)
        queue.append.assert_called_with(event)

    def test__addEvent_drop_duplicate_clear_events(t):
        t.eqm.options.allowduplicateclears = False
        clear_count = 1

        queue = MagicMock(name="queue", spec_set=["append", "__len__"])
        event = {"severity": Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: clear_count}

        t.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        t.assertNotIn(t.eqm.clear_events_count, clear_fingerprint)

        queue.append.assert_not_called()

    def test__addEvent_drop_duplicate_clear_events_interval(t):
        t.eqm.options.allowduplicateclears = False
        clear_count = 3
        t.eqm.options.duplicateclearinterval = clear_count

        queue = MagicMock(name="queue", spec_set=["append", "__len__"])
        event = {"severity": Clear}
        clear_fingerprint = t.eqm._clearFingerprint(event)
        t.eqm.clear_events_count = {clear_fingerprint: clear_count}

        t.eqm._addEvent(queue, event)

        # non-clear events are not added to the clear_events_count dict
        t.assertNotIn(t.eqm.clear_events_count, clear_fingerprint)
        queue.append.assert_not_called()

    def test__addEvent_counts_discarded_events(t):
        queue = MagicMock(name="queue", spec_set=["append", "__len__"])
        event = {}
        discarded_event = {"name": "event"}
        queue.append.return_value = discarded_event

        t.eqm._removeDiscardedEventFromClearState = create_autospec(
            t.eqm._removeDiscardedEventFromClearState,
        )
        t.eqm._discardedEvents.mark = create_autospec(
            t.eqm._discardedEvents.mark
        )

        t.eqm._addEvent(queue, event)

        t.eqm._removeDiscardedEventFromClearState.assert_called_with(
            discarded_event
        )
        t.eqm._discardedEvents.mark.assert_called_with()
        t.assertEqual(t.eqm.discarded_events, 1)

    def test_addEvent(t):
        t.eqm._addEvent = create_autospec(t.eqm._addEvent)
        event = {}
        t.eqm.addEvent(event)

        t.eqm._addEvent.assert_called_with(t.eqm.event_queue, event)

    def test_addPerformanceEvent(t):
        t.eqm._addEvent = create_autospec(t.eqm._addEvent)
        event = {}
        t.eqm.addPerformanceEvent(event)

        t.eqm._addEvent.assert_called_with(t.eqm.perf_event_queue, event)

    def test_addHeartbeatEvent(t):
        heartbeat_event_queue = Mock(spec_set=t.eqm.heartbeat_event_queue)
        t.eqm.heartbeat_event_queue = heartbeat_event_queue
        heartbeat_event = {}
        t.eqm.addHeartbeatEvent(heartbeat_event)

        heartbeat_event_queue.append.assert_called_with(heartbeat_event)

    def test_sendEvents(t):
        """chunks events from EventManager's queues
        yields them to the event_sender_fn
        and returns a deffered with a result of events sent count
        """
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 5
        t.eqm._initQueues()
        heartbeat_events = [{"heartbeat": i} for i in range(2)]
        perf_events = [{"perf_event": i} for i in range(2)]
        events = [{"event": i} for i in range(2)]

        t.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        # heartbeat_event_queue set to static maxlen=1
        t.assertEqual(len(t.eqm.heartbeat_event_queue), 1)
        t.eqm.perf_event_queue.extendleft(perf_events)
        t.eqm.event_queue.extendleft(events)

        event_sender_fn = Mock(name="event_sender_fn")

        ret = t.eqm.sendEvents(event_sender_fn)

        # Priority: heartbeat, perf, event
        event_sender_fn.assert_has_calls(
            [
                call([heartbeat_events[1], perf_events[0], perf_events[1]]),
                call([events[0], events[1]]),
            ]
        )
        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, 5)

    def test_sendEvents_exception_handling(t):
        """In case of exception, places events back in the queue,
        and remove clear state for any discarded events
        """
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 5
        t.eqm._initQueues()
        heartbeat_events = [{"heartbeat": i} for i in range(2)]
        perf_events = [{"perf_event": i} for i in range(2)]
        events = [{"event": i} for i in range(2)]

        t.eqm.heartbeat_event_queue.extendleft(heartbeat_events)
        t.eqm.perf_event_queue.extendleft(perf_events)
        t.eqm.event_queue.extendleft(events)

        def event_sender_fn(args):
            raise Exception("event_sender_fn failed")

        ret = t.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        t.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in defferd exception
        ret.addErrback(Mock())

        # Heartbeat events get dropped
        t.assertNotIn(heartbeat_events[1], t.eqm.heartbeat_event_queue)
        # events and perf_events are returned to the queues
        t.assertIn(perf_events[0], t.eqm.perf_event_queue)
        t.assertIn(events[0], t.eqm.event_queue)

    def test_sendEvents_exception_removes_clear_state_for_discarded(t):
        t.eqm.options.eventflushchunksize = 3
        t.eqm.options.maxqueuelen = 2
        t.eqm._initQueues()
        events = [{"event": i} for i in range(2)]

        t.eqm.event_queue.extendleft(events)

        def send(args):
            t.eqm.event_queue.append({"new_event": 0})
            raise Exception("event_sender_fn failed")

        event_sender_fn = Mock(name="event_sender_fn", side_effect=send)

        t.eqm._removeDiscardedEventFromClearState = create_autospec(
            t.eqm._removeDiscardedEventFromClearState,
            name="_removeDiscardedEventFromClearState",
        )

        ret = t.eqm.sendEvents(event_sender_fn)
        # validate Exception was raised
        t.assertEqual(ret.result.check(Exception), Exception)
        # quash the unhandled error in differd exception
        ret.addErrback(Mock())

        event_sender_fn.assert_called_with([events[0], events[1]])

        t.eqm._removeDiscardedEventFromClearState.assert_called_with(events[0])
