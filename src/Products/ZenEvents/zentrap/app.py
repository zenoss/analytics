##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011-2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zentrap

Creates events from SNMP Traps.
Currently a wrapper around the Net-SNMP C library.
"""

from __future__ import absolute_import, print_function

import socket
import sys
import time

from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall

from zope.component import provideUtility

from Products.ZenCollector.utils.maintenance import ZenHubHeartbeatSender
from Products.ZenEvents.ZenEventClasses import Info
from Products.ZenHub.interfaces import ICollectorEventTransformer
from Products.ZenHub.PBDaemon import PBDaemon
from Products.ZenHub.services.SnmpTrapConfig import User  # noqa: F401

from .capture import Capture
from .filterspec import FilterSpecification
from .handlers import TrapHandler, ReplayTrapHandler
from .net import ipv6_is_enabled
from .oidmap import OidMap
from .receiver import Receiver
from .replay import PacketReplay
from .trapfilter import TrapFilter
from .users import CreateAllUsers

_dropped_events_task_interval = 3600


class TrapDaemon(PBDaemon):
    """
    Daemon for monitoring SNMP traps and sending events derived from
    recieved traps.
    """

    mname = name = "zentrap"

    _cacheservice = "Products.ZenCollector.services.ConfigCache"
    _configservice = "Products.ZenHub.services.SnmpTrapConfig"
    initialServices = PBDaemon.initialServices + [
        _cacheservice,
        _configservice,
    ]

    def __init__(self, *args, **kwargs):
        super(TrapDaemon, self).__init__(*args, **kwargs)

        self.configCycleInterval = 2 * 60  # seconds
        self.cycleInterval = 5 * 60  # seconds

        filterspec = FilterSpecification(self.options.monitor)
        self._trapfilter = TrapFilter(self, filterspec)
        provideUtility(self._trapfilter, ICollectorEventTransformer)
        self._trapfilter_task = None

        self._heartbeat_sender = ZenHubHeartbeatSender(
            self.options.monitor,
            self.name,
            self.options.heartbeatTimeout,
        )
        self._heartbeat_task = None

        self._oidmap = OidMap(self)
        self._oidmap_task = None

        self._createusers = None
        self._createusers_task = None

        self._dropped_events_task = None

        self._receiver = None

    def buildOptions(self):
        super(TrapDaemon, self).buildOptions()
        try:
            TRAP_PORT = socket.getservbyname("snmptrap", "udp")
        except socket.error:
            TRAP_PORT = 162
        self.parser.add_option(
            "--trapport",
            "-t",
            dest="trapport",
            type="int",
            default=TRAP_PORT,
            help="Listen for SNMP traps on this port",
        )
        self.parser.add_option(
            "--useFileDescriptor",
            dest="useFileDescriptor",
            type="int",
            default=None,
            help="Read from an existing connection "
            "rather than opening a new port",
        )
        self.parser.add_option(
            "--varbindCopyMode",
            dest="varbindCopyMode",
            type="int",
            default=2,
            help="Varbind copy mode. Possible values: "
            "0 - the varbinds are copied into event as one field and "
            "ifIndex field is added. "
            "1 - the varbinds are copied into event as several fields "
            "and sequence field is added. "
            "2 - the mixed mode. Uses varbindCopyMode=0 behaviour if "
            "there is only one occurrence of the varbind, otherwise "
            "uses varbindCopyMode=1 behaviour",
        )
        self.parser.add_option(
            "--oidmap-update-interval",
            type="int",
            default=5,
            help="The interval, in minutes, between checks for "
            "updates to the SNMP OID configuration",
        )
        Capture.add_options(self.parser)
        PacketReplay.add_options(self.parser)

    # @override
    def run(self):
        if (
            not self.options.replayFilePrefix
            and not self.options.useFileDescriptor
            and self.options.trapport < 1024
        ):
            self.log.info("opening privileged port %s", self.options.trapport)
            listen_ip = "ipv6" if ipv6_is_enabled() else "0.0.0.0"  # noqa: S104
            # Makes call to zensocket here
            # does an exec* so it never returns
            self.openPrivilegedPort(
                "--listen",
                "--proto=udp",
                "--port=%s:%d" % (listen_ip, self.options.trapport),
            )
            self.log.error("Failed to open privileged port")
            sys.exit(1)

        super(TrapDaemon, self).run()

    # @override
    @defer.inlineCallbacks
    def connected(self):
        # Load the trap filters and oid map before starting tasks.
        # These 'yield' statements are blocking calls within this method.
        yield self._trapfilter.task()
        yield self._oidmap.task()

        replay = PacketReplay.from_options(self.options)
        if replay:
            # A `replay` object was created, so replay previously
            # captured packets.
            self._replay_packets(replay)
        else:
            # Start tasks used for normal (non-replay) operation.
            self._start_dropped_events_task()
            self._start_heartbeat_task()
            self._start_receiver()

    # @override
    def postStatisticsImpl(self):
        if self._receiver is None:
            return
        totalTime, totalEvents, maxTime = self._receiver.handler.stats.report()
        self.rrdStats.counter("events", totalEvents)

    @defer.inlineCallbacks
    def getRemoteConfigCacheProxy(self):
        """Return the remote configuration cache proxy."""
        proxy = yield self.getService(self._cacheservice)
        defer.returnValue(proxy)

    @defer.inlineCallbacks
    def getRemoteConfigServiceProxy(self):
        """Return the remote configuration service proxy object."""
        proxy = yield self.getService(self._configservice)
        defer.returnValue(proxy)

    def _start_dropped_events_task(self):
        self._dropped_events_task = LoopingCall(
            self._send_dropped_trap_count_event
        )
        self._dropped_events_task.start(_dropped_events_task_interval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_dropped_events_task
        )
        self.log.info(
            "started task to send an event with the current "
            "dropped events count"
        )

    def _stop_dropped_events_task(self):
        if self._dropped_events_task is None:
            return
        self._dropped_events_task.stop()
        self._dropped_events_task = None
        self.log.info(
            "stopped task to send an event with the current "
            "dropped events count"
        )

    def _send_dropped_trap_count_event(self):
        counterName = "eventFilterDroppedCount"
        count = self.counters[counterName]
        self.log.info("sma stat event, counter %s: %s", counterName, count)
        counterEvent = {
            "component": "zentrap",
            "device": self.options.monitor,
            "eventClass": "/App/Zenoss",
            "eventKey": "zentrap.{}".format(counterName),
            "summary": "{}: {}".format(counterName, count),
            "severity": Info,
        }
        self.sendEvent(counterEvent)

    def _replay_packets(self, replay):
        handler = ReplayTrapHandler(
            self._oidmap,
            self.options.varbindCopyMode,
            self.options.monitor,
            self,
        )
        for packet in replay:
            handler((packet.host, packet.port), packet, time.time())

    def _start_heartbeat_task(self):
        self._heartbeat_task = LoopingCall(self._heartbeat_sender.heartbeat)
        self._heartbeat_task.start(self.cycleInterval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_heartbeat_task
        )
        self.log.info("started task for sending heartbeats")

    def _stop_heartbeat_task(self):
        if self._heartbeat_task is None:
            return
        self._heartbeat_task.stop()
        self._heartbeat_task = None
        self.log.info("stopped task for sending heartbeats")

    def _start_receiver(self):
        self._start_trapfilter_task()
        self._start_oidmap_task()

        try:
            handler = TrapHandler(
                self._oidmap,
                self.options.varbindCopyMode,
                self.options.monitor,
                self,
            )
            # Attempt to wrap the trap handler in a `Capture` object.
            # If a `Capture` object is created, it becomes the handler.
            capture = Capture.wrap_handler(self.options, handler)
            if capture:
                handler = capture

            self._receiver = Receiver(self.options, handler)

            self._createusers = CreateAllUsers(self, self._receiver)
            self._start_createusers_task()

            self._receiver.start()
            reactor.addSystemEventTrigger(
                "before", "shutdown", self._receiver.stop
            )
            reactor.addSystemEventTrigger(
                "after", "shutdown", self._displayStatistics
            )
        except Exception:
            self.log.exception("failed to initialize receiver")

    def _start_trapfilter_task(self):
        self._trapfilter_task = LoopingCall(self._trapfilter.task)
        self._trapfilter_task.start(self.configCycleInterval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_trapfilter_task
        )
        self.log.info("started task to retrieve trap filters")

    def _stop_trapfilter_task(self):
        if self._trapfilter_task:
            self._trapfilter_task.stop()
            self._trapfilter_task = None
            self.log.info("stopped task to retrieve trap filters")

    def _start_oidmap_task(self):
        self._oidmap_task = LoopingCall(self._oidmap.task)
        self._oidmap_task.start(self.configCycleInterval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_oidmap_task
        )
        self.log.info("started task to retrieve the OID map")

    def _stop_oidmap_task(self):
        if self._oidmap_task:
            self._oidmap_task.stop()
            self._oidmap_task = None
            self.log.info("stopped task to retrieve the OID map")

    def _start_createusers_task(self):
        self._createusers_task = LoopingCall(self._createusers.task)
        self._createusers_task.start(self.configCycleInterval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_createusers_task
        )
        self.log.info("started task to retrieve and create users")

    def _stop_createusers_task(self):
        if self._createusers_task is None:
            return
        self._createusers_task.stop()
        self._createusers_task = None
        self.log.info("stopped task to retrieve and create users")

    def remote_createUser(self, user):
        reactor.callInThread(self._createusers.create_users, [user])

    def _displayStatistics(self):
        totalTime, totalEvents, maxTime = self._receiver.handler.stats.report()
        display = "%d events processed in %.2f seconds" % (
            totalEvents,
            totalTime,
        )
        if totalEvents > 0:
            display += """
%.5f average seconds per event
Maximum processing time for one event was %.5f""" % (
                (totalTime / totalEvents),
                maxTime,
            )
        self.log.info(display)
