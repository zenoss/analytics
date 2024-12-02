##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall
from zenoss.protocols.protobufs.zep_pb2 import DaemonHeartbeat
from zope.component import getUtility

from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenHub.interfaces import IEventService
from Products.ZenMessaging.queuemessaging.interfaces import IQueuePublisher

log = logging.getLogger("zen.maintenance")


def maintenanceBuildOptions(parser, defaultCycle=60):
    """
    Adds option for maintence cycle interval
    """
    parser.add_option(
        "--maintenancecycle",
        dest="maintenancecycle",
        default=defaultCycle,
        type="int",
        help="Cycle, in seconds, for maintenance tasks "
        "[default %s]" % defaultCycle,
    )


class QueueHeartbeatSender(object):
    """
    class for sending heartbeats over amqp
    """

    def __init__(self, monitor, daemon, timeout):
        self._monitor = monitor
        self._daemon = daemon
        self._timeout = timeout

    def heartbeat(self):
        """
        publish the heartbeat
        """
        heartbeat = DaemonHeartbeat(
            monitor=self._monitor,
            daemon=self._daemon,
            timeout_seconds=self._timeout,
        )
        publisher = getUtility(IQueuePublisher)
        publisher.publish(
            "$Heartbeats", "zenoss.heartbeat.%s" % heartbeat.monitor, heartbeat
        )
        log.debug("sent heartbeat %s", heartbeat)


class ZenHubHeartbeatSender(object):
    """
    Default heartbeat sender for CollectorDaemon.
    """

    def __init__(self, monitor, daemon, timeout):
        self.__event = {
            "eventClass": Heartbeat,
            "device": monitor,
            "component": daemon,
            "timeout": timeout
        }

    def heartbeat(self):
        getUtility(IEventService).sendHeartbeat(self.__event)


class MaintenanceCycle(object):
    def __init__(
        self, cycleInterval, heartbeatSender=None, maintenanceCallback=None
    ):
        self.__interval = cycleInterval
        self.__heartbeatSender = heartbeatSender
        self.__callback = maintenanceCallback
        self.__task = LoopingCall(self._maintenance)

    def start(self):
        if self.__interval > 0:
            interval = self.__interval
            self.__task.start(interval, now=True)
        else:
            # maintenance is run only once if _interval <= 0.
            interval = "run-once"
            reactor.callWhenRunning(self._maintenance)
        log.debug("maintenance started  interval=%s", interval)

    def stop(self):
        self.__task.stop()
        log.debug("maintenance stopped")

    @defer.inlineCallbacks
    def _maintenance(self):
        """
        Perform daemon maintenance processing on a periodic schedule.
        """
        if self.__heartbeatSender is not None:
            try:
                yield self.__heartbeatSender.heartbeat()
                log.debug("sent heartbeat")
            except Exception:
                log.exception("failed to send heartbeat")
        if self.__callback is not None:
            try:
                yield self.__callback()
                log.debug("executed maintenance callback")
            except Exception:
                log.exception("failed to execute maintenance callback")
        log.debug("performed periodic maintanence")
