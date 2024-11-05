##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import os
import signal
import socket
import time
from amqplib.client_0_8.exceptions import AMQPConnectionException
from zope.component import getUtility
from Products.ZenEvents.zeneventd import BaseQueueConsumerTask, EventPipelineProcessor
from Products.ZenEvents.zeneventd import QUEUE_RAW_ZEN_EVENTS
from Products.ZenMessaging.queuemessaging.eventlet import BasePubSubMessageTask
from Products.ZenUtils.ZCmdBase import ZCmdBase
from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.jsonformat import to_dict
from zenoss.protocols.eventlet.amqp import Publishable, getProtobufPubSub
from Products.ZenCollector.utils.workers import workersBuildOptions
from Products.ZenUtils.path import zenPath

from metrology import Metrology

log = logging.getLogger("zen.eventd")


class EventletQueueConsumerTask(BaseQueueConsumerTask, BasePubSubMessageTask):

    def __init__(self, processor):
        BaseQueueConsumerTask.__init__(self, processor)
        self.processing_timer = Metrology.timer('processMessage')

    def processMessage(self, message):
        """
        Handles a queue message, can call "acknowledge" on the Queue Consumer
        class when it is done with the message
        """
        with self.processing_timer:
            zepRawEvent = self.processor.processMessage(message)

        if log.isEnabledFor(logging.DEBUG):
            log.debug("Publishing event: %s", to_dict(zepRawEvent))

        yield Publishable(zepRawEvent, exchange=self._dest_exchange,
            routingKey=self._routing_key(zepRawEvent))


class EventDEventletWorker(ZCmdBase):

    mname = 'ZenEventD' # For logging

    def __init__(self):
        super(EventDEventletWorker, self).__init__()
        self._amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        self._queueSchema = getUtility(IQueueSchema)

    def run(self):
        self._shutdown = False
        signal.signal(signal.SIGTERM, self._sigterm)
        mypid = str(os.getpid())
        log.info("in worker, current pid: %s", mypid)
        task = EventletQueueConsumerTask(EventPipelineProcessor(self.dmd))
        self._listen(task)

    def shutdown(self):
        self._shutdown = True
        if self._pubsub:
            self._pubsub.shutdown()
            self._pubsub = None

    def buildOptions(self):
        super(EventDEventletWorker, self).buildOptions()
        # don't comment out the workers option in zeneventd.conf (ZEN-2769)
        workersBuildOptions(self.parser)
        self.parser.add_option('--messagesperworker', dest='messagesPerWorker', default=1,
                    type="int",
                    help='Sets the number of messages each worker gets from the queue at any given time. Default is 1. '
                    'Change this only if event processing is deemed slow. Note that increasing the value increases the '
                    'probability that events will be processed out of order.')
        self.parser.add_option('--maxpickle', dest='maxpickle', default=100, type="int",
                    help='Sets the number of pickle files in var/zeneventd/failed_transformed_events.')
        self.parser.add_option('--pickledir', dest='pickledir', default=zenPath('var/zeneventd/failed_transformed_events'),
                    type="string", help='Sets the path to save pickle files.')

    def _sigterm(self, signum=None, frame=None):
        log.debug("worker sigterm...")
        self.shutdown()

    def _listen(self, task, retry_wait=30):
        self._pubsub = None
        keepTrying = True
        sleep = 0
        while keepTrying and not self._shutdown:
            try:
                if sleep:
                    log.info("Waiting %s seconds to reconnect...", sleep)
                    time.sleep(sleep)
                    sleep = min(retry_wait, sleep * 2)
                else:
                    sleep = .1
                log.info("Connecting to RabbitMQ...")
                self._pubsub = getProtobufPubSub(self._amqpConnectionInfo, self._queueSchema, QUEUE_RAW_ZEN_EVENTS)
                self._pubsub.registerHandler('$Event', task)
                self._pubsub.registerExchange('$ZepZenEvents')
                self._pubsub.messagesPerWorker = self.options.messagesPerWorker
                #reset sleep time
                sleep=0
                self._pubsub.run()
            except (socket.error, AMQPConnectionException) as e:
                log.warn("RabbitMQ Connection error %s", e)
            except KeyboardInterrupt:
                keepTrying = False
            finally:
                if self._pubsub:
                    self._pubsub.shutdown()
                    self._pubsub = None

