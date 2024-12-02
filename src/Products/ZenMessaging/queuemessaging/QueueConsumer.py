##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from zenoss.protocols.interfaces import IAMQPConnectionInfo, IQueueSchema
from zenoss.protocols.twisted.amqp import AMQPFactory
from zope.component import getUtility

from .interfaces import IQueueConsumerTask

log = logging.getLogger("zen.queueconsumer")


class QueueConsumer(object):
    """
    Listens to the model change queue and translates the
    events into graph protobufs
    """

    MARKER = str(hash(object()))

    def __init__(self, task, dmd, amqpConnectionInfo=None, queueSchema=None):
        self.dmd = dmd
        if not amqpConnectionInfo:
            amqpConnectionInfo = getUtility(IAMQPConnectionInfo)
        if not queueSchema:
            queueSchema = getUtility(IQueueSchema)
        self.consumer = AMQPFactory(amqpConnectionInfo, queueSchema)
        self.onReady = self._ready()
        if not IQueueConsumerTask.providedBy(task):
            raise AssertionError(
                "%s does not implement IQueueConsumerTask" % task
            )
        self.task = task
        self.task.dmd = self.dmd
        # give a reference to the consumer to the task
        self.task.queueConsumer = self
        self.shuttingDown = False

    def authenticated(self):
        return self.consumer._onAuthenticated

    def connectionLost(self):
        return self.consumer._onConnectionLost

    def connectionMade(self):
        return self.consumer._onConnectionMade

    def connectionFailed(self):
        return self.consumer._onConnectionFailed

    def _ready(self):
        """
        Calls back once everything's ready and test message went through.
        """
        df = self.consumer._onConnectionMade

        def logCb(result):
            log.info("Queue consumer ready.")
            return result

        df.addCallback(logCb)
        return df

    def setPrefetch(self, prefetch):
        if hasattr(self.consumer, "setPrefetch"):
            self.consumer.setPrefetch(prefetch)

    def run(self):
        """
        Tell all the services to start up. Begin listening for queue messages.
        """
        task = self.task
        log.debug("listening to %s queue", task.queue.name)
        self.consumer.listen(task.queue, callback=task.processMessage)
        return self.onReady

    def shutdown(self, *args):
        """
        Tell all the services to shut down.
        """
        self.shuttingDown = True
        return self.consumer.shutdown()

    def acknowledge(self, message):
        """
        Called from a task when it is done successfully processing
        the message
        """
        return self.consumer.acknowledge(message)

    def reject(self, message, requeue=False):
        """
        Called from a task when it wants to reject and optionally requeue
        a message.
        """
        return self.consumer.reject(message, requeue)

    def publishMessage(
        self,
        exchange,
        routing_key,
        message,
        mandatory=False,
        headers=None,
        declareExchange=True,
    ):
        """
        Publishes a message to another queue. This is for tasks that are both
        consumers and producers.
        """
        return self.consumer.send(
            exchange, routing_key, message, mandatory, headers, declareExchange
        )

    def syncdb(self):
        self.dmd.getPhysicalRoot()._p_jar.sync()
