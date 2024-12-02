##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os

from traceback import format_exc
from twisted.internet import reactor, defer

from zenoss.protocols.queueschema import SchemaException
from zenoss.protocols import hydrateQueueMessage
from zenoss.protocols.interfaces import IQueueSchema
from Products.ZenCallHome.transport.cycler import CallHomeCycler
from Products.ZenCollector.utils.maintenance import MaintenanceCycle, maintenanceBuildOptions, QueueHeartbeatSender
from Products.ZenCollector.utils.workers import ProcessWorkers, workersBuildOptions, exec_worker

from Products.ZenEvents.Schedule import Schedule
from Products.ZenUtils.MetricReporter import TwistedMetricReporter
from Products.ZenUtils.metricwriter import MetricWriter
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import getDefaultZopeUrl
from Products.ZenHub.metricpublisher import publisher

from Products.ZenModel.actions import ActionMissingException, TargetableAction, ActionExecutionException
from Products.ZenModel.interfaces import IAction
from Products.ZenEvents.Event import Event
from Products.ZenMessaging.queuemessaging.QueueConsumer import QueueConsumer
from Products.ZenMessaging.queuemessaging.interfaces import IQueueConsumerTask
from Products.ZenEvents.ZenEventClasses import Warning as SEV_WARNING
from Products.ZenEvents.NotificationDao import NotificationDao
from zope.component import getUtility, getUtilitiesFor
from zope.component.interfaces import ComponentLookupError
from zope.interface import implements

from Products.ZenEvents.interfaces import ISignalProcessorTask

from metrology import Metrology


import logging
log = logging.getLogger("zen.zenactiond")
import transaction

DEFAULT_MONITOR = "localhost"


class ProcessSignalTask(object):
    implements(IQueueConsumerTask, ISignalProcessorTask)

    def __init__(self, notificationDao):
        self.notificationDao = notificationDao
        self.signal_timer = Metrology.timer('zenactiond.signals')
        self.notification_timer = Metrology.timer('zenactiond.notifications')

        # set by the constructor of queueConsumer
        self.queueConsumer = None

        self.schema = getUtility(IQueueSchema)
        self.queue = self.schema.getQueue("$Signals")

    def getAction(self, action):
        try:
            return getUtility(IAction, action)
        except ComponentLookupError:
            raise ActionMissingException(action)

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        log.debug('processing message.')

        chan = self.queueConsumer.consumer.p.chan
        if not getattr(chan, '_flag_qos', False):
            chan.basic_qos(prefetch_count=ZenActionD.MSGS_TO_PREFETCH)
            chan._flag_qos = True

        if message.content.body == self.queueConsumer.MARKER:
            log.info("Received MARKER sentinel, exiting message loop")
            self.queueConsumer.acknowledge(message)
            return
        try:
            signal = hydrateQueueMessage(message, self.schema)
            with self.signal_timer:
                self.processSignal(signal)
            log.debug('Done processing signal.')
        except SchemaException:
            log.error("Unable to hydrate protobuf %s. ", message.content.body)
            self.queueConsumer.acknowledge(message)
        except Exception as e:
            log.exception(e)
            # FIXME: Send to an error queue instead of acknowledge.
            log.error('Acknowledging broken message.')
            self.queueConsumer.acknowledge(message)
        else:
            log.debug('Acknowledging message. (%s)', signal.message)
            self.queueConsumer.acknowledge(message)

    def processSignal(self, signal):
        matches = self.notificationDao.getSignalNotifications(signal)
        log.debug('Found these matching notifications: %s', matches)

        trigger = self.notificationDao.guidManager.getObject(signal.trigger_uuid)
        audit_event_trigger_info = "Event:'%s' Trigger:%s" % (
                                        signal.event.occurrence[0].fingerprint,
                                        trigger.id)
        for notification in matches:
            if signal.clear and not notification.send_clear:
                log.debug('Ignoring clearing signal since send_clear is set to False on this subscription %s', notification.id)
                continue

            if self.shouldSuppress(notification, signal, trigger.id):
                log.debug('Suppressing notification %s', notification.id)
                continue

            try:
                target = signal.subscriber_uuid or '<none>'
                action = self.getAction(notification.action)
                action.setupAction(notification.dmd)
                if isinstance(action, TargetableAction):
                    target = ','.join(action.getTargets(notification, signal))
                with self.notification_timer:
                    action.execute(notification, signal)
            except ActionMissingException as e:
                log.error('Error finding action: %s', notification.action)
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, "<action not found>")
            except ActionExecutionException as aee:
                log.error('Error executing action: %s on notification %s',
                    notification.action,
                    notification.id,
                )
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, aee)
            except Exception as e:
                msg = 'Error executing action {notification}'.format(
                    notification = notification.id,
                )
                log.exception(e)
                log.error(msg)
                traceback = format_exc()
                event = Event(device="localhost",
                              eventClass="/App/Failed",
                              summary=msg,
                              message=traceback,
                              severity=SEV_WARNING, component="zenactiond")
                self.dmd.ZenEventManager.sendEvent(event)
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "FAIL", target, action.getInfo(notification))
            else:
                # audit trail of performed actions
                audit_msg =  "%s Action:%s Status:%s Target:%s Info:%s" % (
                                    audit_event_trigger_info, notification.action, "SUCCESS", target, action.getInfo(notification))
                self.recordNotification(notification, signal, trigger.id)

            log.info(audit_msg)
        log.debug('Done processing signal. (%s)', signal.message)

    def shouldSuppress(self, notification, signal, triggerId):
        return False

    def recordNotification(self, notification, signal, triggerId):
        pass


class ZenActionD(ZCmdBase):

    MSGS_TO_PREFETCH = 1

    def __init__(self):
        super(ZenActionD, self).__init__()
        self._consumer = None
        self._workers = ProcessWorkers(self.options.workers - 1,
                                       exec_worker,
                                       "zenactiond worker")
        self._heartbeatSender = QueueHeartbeatSender('localhost',
                                                 'zenactiond',
                                                 self.options.heartbeatTimeout)

        self._maintenanceCycle = MaintenanceCycle(self.options.maintenancecycle,
                                                  self._heartbeatSender)
        self._callHomeCycler = CallHomeCycler(self.dmd)
        self._schedule = Schedule(self.options, self.dmd)
        self._schedule.sendEvent = self.dmd.ZenEventManager.sendEvent
        self._schedule.monitor = self.options.monitor

    def buildOptions(self):
        super(ZenActionD, self).buildOptions()
        maintenanceBuildOptions(self.parser)
        workersBuildOptions(self.parser, 1)

        default_max_commands = 10
        self.parser.add_option('--maxcommands', dest="maxCommands", type="int", default=default_max_commands,
                               help='Max number of action commands to perform concurrently (default: %d)' % \
                                    default_max_commands)
        default_max_pagingworkers = 1
        self.parser.add_option('--maxpagingworkers', dest="maxPagingWorkers", type="int", default=default_max_pagingworkers,
                               help='max number of paging workers to perform concurrently (default: %d)' % \
                                       default_max_pagingworkers)
        default_pagingworkers_timeout = 30
        self.parser.add_option('--pagingworkerstimeout', dest="pagingWorkersTimeout", type="int", default=default_pagingworkers_timeout,
                               help='Timeout, in seconds, for paging workers (default: %d)' % \
                                       default_pagingworkers_timeout)
        default_url = getDefaultZopeUrl()
        self.parser.add_option('--zopeurl', dest='zopeurl', default=default_url,
                               help="http path to the root of the zope server (default: %s)" % default_url)
        self.parser.add_option("--monitor", dest="monitor",
            default=DEFAULT_MONITOR,
            help="Name of monitor instance to use for heartbeat "
                " events. Default is %s." % DEFAULT_MONITOR)
        self.parser.add_option('--maintenance-window-cycletime',
            dest='maintenceWindowCycletime', default=60, type="int",
            help="How often to check to see if there are any maintenance windows to execute")
        self.parser.add_option('--maintenance-window-batch-size',
            dest='maintenceWindowBatchSize', default=200, type="int",
            help="How many devices update per one transaction on maintenance windows execution")
        self.parser.add_option('--strip-email-body-tags',
            dest='stripEmailBodyTags', default=True, action="store_false",
            help="Strip HTML/XML tags from plaintext email notifications?")

        self.parser.add_option("--workerid", dest='workerid', type='int', default=None,
                               help="ID of the worker instance.")

    def run(self):
        # Configure all actions with the command-line options
        self.abortIfWaiting()
        options_dict = dict(vars(self.options))
        for name, action in getUtilitiesFor(IAction):
            action.configure(options_dict)

        dao = NotificationDao(self.dmd)
        task = ISignalProcessorTask(dao)
        metric_destination = os.environ.get("CONTROLPLANE_CONSUMER_URL", "")
        if metric_destination == "":
            metric_destination = "http://localhost:22350/api/metrics/store"
        username = os.environ.get("CONTROLPLANE_CONSUMER_USERNAME", "")
        password = os.environ.get("CONTROLPLANE_CONSUMER_PASSWORD", "")
        pub = publisher.HttpPostPublisher(username, password, metric_destination)

        log.debug("Creating async MetricReporter")
        daemonTags = {
            'zenoss_daemon': 'zenactiond',
            'internal': True
        }
        self.metricreporter = TwistedMetricReporter(prefix='zenoss.', metricWriter=MetricWriter(pub), tags=daemonTags)
        self.metricreporter.start()
        reactor.addSystemEventTrigger('before', 'shutdown', self.metricreporter.stop)

        if self.options.workerid == 0 and (self.options.daemon or self.options.cycle):
            self._callHomeCycler.start()
            self._schedule.start()  # maintenance windows

        if self.options.daemon or self.options.cycle:
            self._maintenanceCycle.start()  # heartbeats, etc.

        if (self.options.daemon or self.options.cycle) and self.options.workers > 1:
            self._workers.startWorkers()

        self._consumer = QueueConsumer(task, self.dmd)
        reactor.callWhenRunning(self._start)
        reactor.run()

    def abortIfWaiting(self):
        # If this process is doing nothing, abort the transaction to avoid long INNODB history
        try:
            transaction.abort()
        except Exception:
            pass
        reactor.callLater(30.0, self.abortIfWaiting)

    def _start(self):
        log.info('starting zenactiond consumer.')
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)
        self._consumer.run()


    @defer.inlineCallbacks
    def _shutdown(self, *ignored):
        log.info("Shutting down...")
        self._maintenanceCycle.stop()
        self._workers.shutdown()
        if self._consumer:
            yield self._consumer.shutdown()


if __name__ == '__main__':
    zad = ZenActionD()
    zad.run()
