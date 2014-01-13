##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from twisted.internet import reactor
from twisted.internet import defer

import time
from datetime import datetime, timedelta

import Globals
from zope.component import getUtility, adapter

from zope.interface import implements
from zope.component.event import objectEventNotify

from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.guid import guid
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.protobufs.zep_pb2 import ZepRawEvent, Event, STATUS_DROPPED
from zenoss.protocols.jsonformat import from_dict, to_dict
from zenoss.protocols import hydrateQueueMessage
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenEvents.events2.processing import (Manager, EventPluginPipe, CheckInputPipe, IdentifierPipe,
    AddDeviceContextAndTagsPipe, TransformAndReidentPipe, TransformPipe, UpdateDeviceContextAndTagsPipe,
    AssignDefaultEventClassAndTagPipe, FingerprintPipe, SerializeContextPipe, ClearClassRefreshPipe,
    EventContext, DropEvent, ProcessingException, CheckHeartBeatPipe)
from Products.ZenEvents.interfaces import IPreEventPlugin, IPostEventPlugin
from Products.ZenEvents.daemonlifecycle import DaemonCreatedEvent, SigTermEvent, SigUsr1Event
from Products.ZenEvents.daemonlifecycle import DaemonStartRunEvent, BuildOptionsEvent

import logging
log = logging.getLogger("zen.eventd")

EXCHANGE_ZEP_ZEN_EVENTS = '$ZepZenEvents'
QUEUE_RAW_ZEN_EVENTS = '$RawZenEvents'

class EventPipelineProcessor(object):

    SYNC_EVERY_EVENT = False

    def __init__(self, dmd):
        self.dmd = dmd
        self._manager = Manager(self.dmd)
        self._pipes = (
            EventPluginPipe(self._manager, IPreEventPlugin, 'PreEventPluginPipe'),
            CheckInputPipe(self._manager),
            IdentifierPipe(self._manager),
            AddDeviceContextAndTagsPipe(self._manager),
            TransformAndReidentPipe(self._manager,
                TransformPipe(self._manager),
                [
                UpdateDeviceContextAndTagsPipe(self._manager),
                IdentifierPipe(self._manager),
                AddDeviceContextAndTagsPipe(self._manager),
                ]),
            AssignDefaultEventClassAndTagPipe(self._manager),
            FingerprintPipe(self._manager),
            SerializeContextPipe(self._manager),
            EventPluginPipe(self._manager, IPostEventPlugin, 'PostEventPluginPipe'),
            ClearClassRefreshPipe(self._manager),
            CheckHeartBeatPipe(self._manager)
        )

        if not self.SYNC_EVERY_EVENT:
            # don't call sync() more often than 1 every 0.5 sec - helps throughput
            # when receiving events in bursts
            self.nextSync = datetime.now()
            self.syncInterval = timedelta(0,0,500000)

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """

        if self.SYNC_EVERY_EVENT:
            doSync = True
        else:
            # sync() db if it has been longer than self.syncInterval since the last time
            currentTime = datetime.now()
            doSync = currentTime > self.nextSync
            self.nextSync = currentTime + self.syncInterval

        if doSync:
            self.dmd._p_jar.sync()

        try:
            retry = True
            processed = False
            while not processed:
                try:
                    # extract event from message body
                    zepevent = ZepRawEvent()
                    zepevent.event.CopyFrom(message)
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("Received event: %s", to_dict(zepevent.event))

                    eventContext = EventContext(log, zepevent)

                    for pipe in self._pipes:
                        eventContext = pipe(eventContext)
                        if log.isEnabledFor(logging.DEBUG):
                            log.debug('After pipe %s, event context is %s' % ( pipe.name, to_dict(eventContext.zepRawEvent) ))
                        if eventContext.event.status == STATUS_DROPPED:
                            raise DropEvent('Dropped by %s' % pipe, eventContext.event)

                    processed = True

                except AttributeError:
                    # _manager throws Attribute errors if connection to zope is lost - reset
                    # and retry ONE time
                    if retry:
                        retry=False
                        log.debug("Resetting connection to catalogs")
                        self._manager.reset()
                    else:
                        raise

        except DropEvent:
            # we want these to propagate out
            raise
        except Exception as e:
            log.info("Failed to process event, forward original raw event: %s", to_dict(zepevent.event))
            # Pipes and plugins may raise ProcessingException's for their own reasons - only log unexpected
            # exceptions of other type (will insert stack trace in log)
            if not isinstance(e, ProcessingException):
                log.exception(e)

            # construct wrapper event to report this event processing failure (including content of the
            # original event)
            origzepevent = ZepRawEvent()
            origzepevent.event.CopyFrom(message)
            failReportEvent = dict(
                uuid = guid.generate(),
                created_time = int(time.time()*1000),
                fingerprint='|'.join(['zeneventd', 'processMessage', repr(e)]),
                # Don't send the *same* event class or we trash and and crash endlessly
                eventClass='/',
                summary='Internal exception processing event: %r' % e,
                message='Internal exception processing event: %r/%s' % (e, to_dict(origzepevent.event)),
                severity=4,
            )
            zepevent = ZepRawEvent()
            zepevent.event.CopyFrom(from_dict(Event, failReportEvent))
            eventContext = EventContext(log, zepevent)
            eventContext.eventProxy.device = 'zeneventd'
            eventContext.eventProxy.component = 'processMessage'

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Publishing event: %s", to_dict(eventContext.zepRawEvent))

        return eventContext.zepRawEvent

class BaseQueueConsumerTask(object):

    implements(IQueueConsumerTask)

    def __init__(self, processor):
        self.processor = processor
        self._queueSchema = getUtility(IQueueSchema)
        self.dest_routing_key_prefix = 'zenoss.zenevent'
        self._dest_exchange = self._queueSchema.getExchange(EXCHANGE_ZEP_ZEN_EVENTS)

    def _routing_key(self, event):
        return (self.dest_routing_key_prefix +
                event.event.event_class.replace('/', '.').lower())

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
                    log.debug("Publishing event: %s", to_dict(zepRawEvent))
                yield self.queueConsumer.publishMessage(EXCHANGE_ZEP_ZEN_EVENTS,
                    self._routing_key(zepRawEvent), zepRawEvent, declareExchange=False)
                yield self.queueConsumer.acknowledge(message)
            except DropEvent as e:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug('%s - %s' % (e.message, to_dict(e.event)))
                yield self.queueConsumer.acknowledge(message)
            except ProcessingException as e:
                log.error('%s - %s' % (e.message, to_dict(e.event)))
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
        self._consumer_task = TwistedQueueConsumerTask(EventPipelineProcessor(dmd))
        self._consumer = QueueConsumer(self._consumer_task, dmd)

    def run(self):
        reactor.callWhenRunning(self._start)
        reactor.run()

    def _start(self):
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()

    @defer.inlineCallbacks
    def _shutdown(self):
        if self._consumer:
            yield self._consumer.shutdown()

class ZenEventD(ZCmdBase):

    def __init__(self, *args, **kwargs):
        super(ZenEventD, self).__init__(*args, **kwargs)
        EventPipelineProcessor.SYNC_EVERY_EVENT = self.options.syncEveryEvent
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                     'zeneventd',
                                                     self.options.maintenancecycle *3)
        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                  self._heartbeatSender)
        objectEventNotify(DaemonCreatedEvent(self))

    def sigTerm(self, signum=None, frame=None):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        objectEventNotify(SigTermEvent(self))
        super(ZenEventD, self).sigTerm(signum, frame)

    def run(self):
        if self.options.daemon:
            self._maintenanceCycle.start()
        objectEventNotify(DaemonStartRunEvent(self))

    def sighandler_USR1(self, signum, frame):
        super(ZenEventD, self).sighandler_USR1(signum, frame)
        log.debug('sighandler_USR1 called %s' % signum)
        objectEventNotify(SigUsr1Event(self, signum))

    def buildOptions(self):
        super(ZenEventD, self).buildOptions()
        maintenanceBuildOptions(self.parser)
        self.parser.add_option('--synceveryevent', dest='syncEveryEvent',
                    action="store_true", default=False,
                    help='Force sync() before processing every event; default is to sync() no more often '
                    'than once every 1/2 second.')
        self.parser.add_option('--messagesperworker', dest='messagesPerWorker', default=1,
                    type="int",
                    help='Sets the number of messages each worker gets from the queue at any given time. Default is 1. '
                    'Change this only if event processing is deemed slow. Note that increasing the value increases the '
                    'probability that events will be processed out of order.')
        objectEventNotify(BuildOptionsEvent(self))



if __name__ == '__main__':
    # explicit import of ZenEventD to activate enterprise extensions
    from Products.ZenEvents.zeneventd import ZenEventD
    zed = ZenEventD()
    zed.run()
