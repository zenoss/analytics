##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import signal
from time import time

from twisted.internet import defer, reactor
from zope.component import getUtility, provideUtility
from zope.component.event import objectEventNotify
from zope.interface import implementer, implements
from metrology import Metrology

from zenoss.protocols import hydrateQueueMessage
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.jsonformat import from_dict, to_dict
from zenoss.protocols.protobufs.zep_pb2 import (
    STATUS_DROPPED,
    Event,
    ZepRawEvent,
)

from Products.ZenCollector.utils.maintenance import (
    MaintenanceCycle,
    QueueHeartbeatSender,
    maintenanceBuildOptions,
)
from Products.ZenEvents.daemonlifecycle import (
    BuildOptionsEvent,
    DaemonCreatedEvent,
    DaemonStartRunEvent,
    SigTermEvent,
    SigUsr1Event,
)
from Products.ZenEvents.events2.processing import (
    AddDeviceContextAndTagsPipe,
    AssignDefaultEventClassAndTagPipe,
    CheckHeartBeatPipe,
    CheckInputPipe,
    ClearClassRefreshPipe,
    DropEvent,
    EventContext,
    EventPluginPipe,
    FingerprintPipe,
    IdentifierPipe,
    Manager,
    ProcessingException,
    SerializeContextPipe,
    TransformAndReidentPipe,
    TransformPipe,
    UpdateDeviceContextAndTagsPipe,
)
from Products.ZenEvents.interfaces import IPostEventPlugin, IPreEventPlugin
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenUtils.daemonconfig import IDaemonConfig
from Products.ZenUtils.guid import guid
from Products.ZenUtils.MetricReporter import MetricReporter
from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.ZCmdBase import ZCmdBase


def monkey_patch_rotatingfilehandler():
    try:
        from cloghandler import ConcurrentRotatingFileHandler

        logging.handlers.RotatingFileHandler = ConcurrentRotatingFileHandler
    except ImportError:
        from warnings import warn

        warn(
            "ConcurrentLogHandler package not installed. Using"
            " RotatingFileLogHandler. While everything will still work fine,"
            " there is a potential for log files overlapping each other."
        )


monkey_patch_rotatingfilehandler()

log = logging.getLogger("zen.eventd")

EXCHANGE_ZEP_ZEN_EVENTS = "$ZepZenEvents"
QUEUE_RAW_ZEN_EVENTS = "$RawZenEvents"


class EventPipelineProcessor(object):

    SYNC_EVERY_EVENT = False
    PROCESS_EVENT_TIMEOUT = 0

    def __init__(self, dmd):
        self.dmd = dmd
        self._manager = Manager(self.dmd)
        self._pipes = (
            EventPluginPipe(
                self._manager, IPreEventPlugin, "PreEventPluginPipe"
            ),
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextAndTagsPipe(self._manager),
            TransformAndReidentPipe(
                self._manager,
                TransformPipe(self._manager),
                [
                    UpdateDeviceContextAndTagsPipe(self._manager),
                    IdentifierPipe(self._manager),
                    AddDeviceContextAndTagsPipe(self._manager),
                ],
            ),
            AssignDefaultEventClassAndTagPipe(self._manager),
            FingerprintPipe(self._manager),
            SerializeContextPipe(self._manager),
            EventPluginPipe(
                self._manager, IPostEventPlugin, "PostEventPluginPipe"
            ),
            ClearClassRefreshPipe(self._manager),
            CheckHeartBeatPipe(self._manager),
        )
        self._pipe_timers = {}
        for pipe in self._pipes:
            timer_name = pipe.name
            self._pipe_timers[timer_name] = Metrology.timer(timer_name)

        self.reporter = MetricReporter(prefix="zenoss.zeneventd.")
        self.reporter.start()

        if not self.SYNC_EVERY_EVENT:
            # don't call sync() more often than 1 every 0.5 sec
            # helps throughput when receiving events in bursts
            self.nextSync = time()
            self.syncInterval = 0.5

    def processMessage(self, message, retry=True):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        self._synchronize_with_database()

        try:
            # extract event from message body
            zepevent = ZepRawEvent()
            zepevent.event.CopyFrom(message)
            if log.isEnabledFor(logging.DEBUG):
                # assume to_dict() is expensive.
                log.debug("Received event: %s", to_dict(zepevent.event))
            eventContext = EventContext(log, zepevent)

            with Timeout(
                zepevent,
                self.PROCESS_EVENT_TIMEOUT,
                error_message="while processing event",
            ):
                for pipe in self._pipes:
                    with self._pipe_timers[pipe.name]:
                        eventContext = pipe(eventContext)
                    if log.isEnabledFor(logging.DEBUG):
                        # assume to_dict() is expensive.
                        log.debug(
                            "After pipe %s, event context is %s",
                            pipe.name,
                            to_dict(eventContext.zepRawEvent),
                        )
                    if eventContext.event.status == STATUS_DROPPED:
                        raise DropEvent(
                            "Dropped by %s" % pipe, eventContext.event
                        )

        except AttributeError:
            # _manager throws Attribute errors
            # if connection to zope is lost - reset and retry ONE time
            if retry:
                log.debug("Resetting connection to catalogs")
                self._manager.reset()
                self.processMessage(message, retry=False)
            else:
                raise

        except DropEvent:
            # we want these to propagate out
            raise

        except Exception as error:
            log.info(
                "Failed to process event, forward original raw event: %s",
                to_dict(zepevent.event),
            )
            # Pipes and plugins may raise ProcessingException's for their own
            # reasons. only log unexpected exceptions of other type
            # will insert stack trace in log
            if not isinstance(error, ProcessingException):
                log.exception(error)

            eventContext = self.create_exception_event(message, error)

        if log.isEnabledFor(logging.DEBUG):
            # assume to_dict() is expensive.
            log.debug(
                "Publishing event: %s", to_dict(eventContext.zepRawEvent)
            )
        return eventContext.zepRawEvent

    def _synchronize_with_database(self):
        """sync() db if it has been longer than
        self.syncInterval seconds since the last time,
        and no _synchronize has not been called for self.syncInterval seconds
        KNOWN ISSUE: ZEN-29884
        """
        if self.SYNC_EVERY_EVENT:
            doSync = True
        else:
            current_time = time()
            doSync = current_time > self.nextSync
            self.nextSync = current_time + self.syncInterval

        if doSync:
            self.dmd._p_jar.sync()

    def create_exception_event(self, message, exception):
        # construct wrapper event to report this event processing failure
        # including content of the original event
        orig_zep_event = ZepRawEvent()
        orig_zep_event.event.CopyFrom(message)
        failure_event = {
            "uuid": guid.generate(),
            "created_time": int(time() * 1000),
            "fingerprint": "|".join(
                ["zeneventd", "processMessage", repr(exception)]
            ),
            # Don't send the *same* event class or we loop endlessly
            "eventClass": "/",
            "summary": "Internal exception processing event: %r" % exception,
            "message": "Internal exception processing event: %r/%s"
            % (exception, to_dict(orig_zep_event.event)),
            "severity": 4,
        }
        zep_raw_event = ZepRawEvent()
        zep_raw_event.event.CopyFrom(from_dict(Event, failure_event))
        event_context = EventContext(log, zep_raw_event)
        event_context.eventProxy.device = "zeneventd"
        event_context.eventProxy.component = "processMessage"
        return event_context


class BaseQueueConsumerTask(object):

    implements(IQueueConsumerTask)

    def __init__(self, processor):
        self.processor = processor
        self._queueSchema = getUtility(IQueueSchema)
        self.dest_routing_key_prefix = "zenoss.zenevent"
        self._dest_exchange = self._queueSchema.getExchange(
            EXCHANGE_ZEP_ZEN_EVENTS
        )

    def _routing_key(self, event):
        return (
            self.dest_routing_key_prefix
            + event.event.event_class.replace("/", ".").lower()
        )


class TwistedQueueConsumerTask(BaseQueueConsumerTask):
    def __init__(self, processor):
        BaseQueueConsumerTask.__init__(self, processor)
        self.queue = self._queueSchema.getQueue(QUEUE_RAW_ZEN_EVENTS)

    @defer.inlineCallbacks
    def processMessage(self, message):
        try:
            hydrated = hydrateQueueMessage(message, self._queueSchema)
        except Exception as e:
            log.error("Failed to hydrate raw event: %s", e)
            yield self.queueConsumer.acknowledge(message)
        else:
            try:
                zepRawEvent = self.processor.processMessage(hydrated)
                if log.isEnabledFor(logging.DEBUG):
                    # assume to_dict() is expensive.
                    log.debug("Publishing event: %s", to_dict(zepRawEvent))
                yield self.queueConsumer.publishMessage(
                    EXCHANGE_ZEP_ZEN_EVENTS,
                    self._routing_key(zepRawEvent),
                    zepRawEvent,
                    declareExchange=False,
                )
                yield self.queueConsumer.acknowledge(message)
            except DropEvent as e:
                if log.isEnabledFor(logging.DEBUG):
                    # assume to_dict() is expensive.
                    log.debug("%s - %s", e.message, to_dict(e.event))
                yield self.queueConsumer.acknowledge(message)
            except ProcessingException as e:
                log.error("%s - %s", e.message, to_dict(e.event))
                log.exception(e)
                yield self.queueConsumer.reject(message)
            except Exception as e:
                log.exception(e)
                yield self.queueConsumer.reject(message)


class EventDTwistedWorker(object):
    def __init__(self, dmd):
        super(EventDTwistedWorker, self).__init__()
        self._amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        self._queueSchema = getUtility(IQueueSchema)
        self._consumer_task = TwistedQueueConsumerTask(
            EventPipelineProcessor(dmd)
        )
        self._consumer = QueueConsumer(self._consumer_task, dmd)

    def run(self):
        reactor.callWhenRunning(self._start)
        reactor.run()

    def _start(self):
        reactor.addSystemEventTrigger("before", "shutdown", self._shutdown)
        self._consumer.run()

    @defer.inlineCallbacks
    def _shutdown(self):
        if self._consumer:
            yield self._consumer.shutdown()


@implementer(IDaemonConfig)
class ZenEventDConfig:
    def __init__(self, options):
        self.options = options

    def getConfig(self):
        return self.options


class ZenEventD(ZCmdBase):
    def __init__(self, *args, **kwargs):
        super(ZenEventD, self).__init__(*args, **kwargs)
        EventPipelineProcessor.SYNC_EVERY_EVENT = self.options.syncEveryEvent
        EventPipelineProcessor.PROCESS_EVENT_TIMEOUT = (
            self.options.process_event_timeout
        )
        self._heartbeatSender = QueueHeartbeatSender(
            "localhost", "zeneventd", self.options.heartbeatTimeout
        )
        self._maintenanceCycle = MaintenanceCycle(
            self.options.maintenancecycle, self._heartbeatSender
        )
        objectEventNotify(DaemonCreatedEvent(self))
        config = ZenEventDConfig(self.options)
        provideUtility(config, IDaemonConfig, "zeneventd_config")

    def sigTerm(self, signum=None, frame=None):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        objectEventNotify(SigTermEvent(self))
        super(ZenEventD, self).sigTerm(signum, frame)

    def run(self):
        if self.options.daemon or self.options.cycle:
            self._maintenanceCycle.start()
        objectEventNotify(DaemonStartRunEvent(self))

    def sighandler_USR1(self, signum, frame):
        super(ZenEventD, self).sighandler_USR1(signum, frame)
        log.debug("sighandler_USR1 called %s", signum)
        objectEventNotify(SigUsr1Event(self, signum))

    def buildOptions(self):
        super(ZenEventD, self).buildOptions()
        maintenanceBuildOptions(self.parser)
        self.parser.add_option(
            "--synceveryevent",
            dest="syncEveryEvent",
            action="store_true",
            default=False,
            help=(
                "Force sync() before processing every event; default is"
                " to sync() no more often than once every 1/2 second."
            ),
        )
        self.parser.add_option(
            "--process-event-timeout",
            dest="process_event_timeout",
            type="int",
            default=0,
            help=(
                "Set the Timeout(in seconds) for processing each event."
                " The timeout may be extended for a transforms using,"
                "signal.alarm(<timeout seconds>) in the transform"
                "set to 0 to disable"
            ),
        )
        self.parser.add_option(
            "--messagesperworker",
            dest="messagesPerWorker",
            default=1,
            type="int",
            help=(
                "Sets the number of messages each worker gets from the queue"
                " at any given time. Default is 1. Change this only if event"
                " processing is deemed slow. Note that increasing the value"
                " increases the probability that events will be processed"
                " out of order."
            ),
        )
        self.parser.add_option(
            "--maxpickle",
            dest="maxpickle",
            default=100,
            type="int",
            help=(
                "Sets the number of pickle files in"
                " var/zeneventd/failed_transformed_events."
            ),
        )
        self.parser.add_option(
            "--pickledir",
            dest="pickledir",
            default=zenPath("var", "zeneventd", "failed_transformed_events"),
            type="string",
            help="Sets the path to save pickle files.",
        )
        objectEventNotify(BuildOptionsEvent(self))


class Timeout:
    def __init__(self, event, seconds=1, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message
        self.event = event

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message, self.event)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


class TimeoutError(Exception):
    def __init__(self, message, event=None):
        super(TimeoutError, self).__init__(message)
        self.event = event


if __name__ == "__main__":
    # explicit import of ZenEventD to activate enterprise extensions
    from Products.ZenEvents.zeneventd import ZenEventD  # noqa F811

    zed = ZenEventD()
    zed.run()
