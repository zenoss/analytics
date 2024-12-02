from unittest import TestCase
from mock import patch, call, Mock, MagicMock

from Products.ZenEvents.zeneventd import (
    CheckInputPipe,
    Event,
    EventContext,
    EventPipelineProcessor,
    time,
    Timeout,
    TimeoutError,
    ZepRawEvent,
)
from Products.ZenEvents.events2.processing import EventProcessorPipe
from zenoss.protocols.protobufs.zep_pb2 import EventActor, EventSeverity
from zenoss.protocols.protobufs.model_pb2 import ModelElementType


PATH = {"zeneventd": "Products.ZenEvents.zeneventd"}


class EventPipelineProcessorTest(TestCase):
    def setUp(self):
        self.dmd = Mock()
        self.log_patcher = patch(
            "{zeneventd}.log".format(**PATH), autospec=True
        )
        self.manager_patcher = patch(
            "{zeneventd}.Manager".format(**PATH), autospec=True
        )
        # silence 'new thread' error
        self.metric_reporter_patcher = patch(
            "{zeneventd}.MetricReporter".format(**PATH), autospec=True
        )
        self.log_patcher.start()
        self.manager_patcher.start()
        self.metric_reporter_patcher.start()

        self.epp = EventPipelineProcessor(self.dmd)

        self.message = Event(
            uuid="75e7c760-39d4-11e8-a97b-0242ac11001a",
            created_time=1523044529575,
            event_class="/ZenossRM",
            actor=EventActor(
                element_type_id=ModelElementType.DEVICE,
                element_uuid="575bcf2d-8ca0-47d9-8e63-b4f2c1242ef3",
                element_identifier="device.loc",
                element_sub_type_id=ModelElementType.COMPONENT,
                element_sub_identifier="zeneventd",
            ),
            summary="Event Summary",
            severity=EventSeverity.SEVERITY_DEBUG,
            event_key="RMMonitor.collect.docker",
            agent="zenpython",
            monitor="localhost",
            first_seen_time=1523044529575,
        )

    def tearDown(self):
        self.log_patcher.stop()
        self.manager_patcher.stop()
        self.metric_reporter_patcher.stop()

    def test_processMessage(self):
        self.epp._pipes = (CheckInputPipe(self.epp._manager),)

        zep_raw_event = self.epp.processMessage(self.message)

        self.assertIsInstance(zep_raw_event, ZepRawEvent)
        self.assertIsInstance(zep_raw_event.event, Event)
        self.assertEqual(zep_raw_event.event.message, self.message.summary)

    def test_exception_in_pipe(self):
        error_pipe = self.ErrorPipe(self.epp._manager)
        self.epp._pipes = (error_pipe,)
        self.epp._pipe_timers[error_pipe.name] = MagicMock()

        zep_raw_event = self.epp.processMessage(self.message)

        self.assertIsInstance(zep_raw_event, ZepRawEvent)
        self.assertIsInstance(zep_raw_event.event, Event)

        exception_event = self.epp.create_exception_event(
            self.message, self.ErrorPipe.ERR
        )

        self.assertEqual(
            zep_raw_event.event.message, exception_event.event.message
        )

    class ErrorPipe(EventProcessorPipe):
        ERR = Exception("pipeline failure")

        def __call__(self, eventContext):
            raise self.ERR

    def test_synchronize_with_database(self):
        self.epp._synchronize_with_database()
        self.dmd._p_jar.sync.assert_called_once_with()

    def test_synchronize_with_database_delay(self):
        self.epp.nextSync = time() + 0.5
        self.epp._synchronize_with_database()
        self.dmd._p_jar.sync.assert_not_called()

    def test_synchronize_with_database_every_event(self):
        self.epp.SYNC_EVERY_EVENT = True
        self.epp.nextSync = time() + 0.5
        self.epp._synchronize_with_database()
        self.dmd._p_jar.sync.assert_called_once_with()

    def test_create_exception_event(self):
        error = Exception("test exception")
        event_context = self.epp.create_exception_event(self.message, error)
        self.assertIsInstance(event_context, EventContext)

        exception_event = event_context.event

        self.assertIsInstance(exception_event, Event)
        self.assertEqual(
            exception_event.summary,
            "Internal exception processing event: "
            "Exception('test exception',)",
        )
        self.assertTrue(str(error) in exception_event.message)


class TimeoutTest(TestCase):
    def setUp(self):
        # Patch external dependencies
        self.signal_patcher = patch(
            "{zeneventd}.signal".format(**PATH), autospec=True
        )
        self.signal = self.signal_patcher.start()

    def tearDown(self):
        self.signal_patcher.stop()

    def test_context_manager(self):
        timeout_duration = 10

        with Timeout("event", timeout_duration) as ctx:
            self.signal.signal.assert_called_with(
                self.signal.SIGALRM, ctx.handle_timeout
            )

        self.signal.alarm.assert_has_calls([call(timeout_duration), call(0)])

    def test_handle_timeout_raises_exception(self):
        with self.assertRaises(TimeoutError):
            with Timeout(1) as ctx:
                ctx.handle_timeout(1, "frame")


class BaseQueueConsumerTaskTest(TestCase):
    pass


class TwistedQueueConsumerTaskTest(TestCase):
    pass


class EventDTwistedWorkerTest(TestCase):
    pass


class ZenEventDTest(TestCase):
    pass
