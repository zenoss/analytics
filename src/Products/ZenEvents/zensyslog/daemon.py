##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2011, 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import socket
import sys

from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall
from zope.component import provideUtility

from Products.ZenCollector.utils.maintenance import ZenHubHeartbeatSender
from Products.ZenEvents.ZenEventClasses import Info
from Products.ZenHub.interfaces import ICollectorEventTransformer
from Products.ZenHub.PBDaemon import PBDaemon

from .loader import ConfigLoader
from .loggers import DropLogger, MessageLogger, RawFormatter, HumanFormatter
from .processor import Parsers, SyslogProcessor
from .protocol import SyslogProtocol
from .receiver import AdoptPort, CreatePort, Receiver
from .transformer import FilterRules, SyslogMsgFilter

_dropped_counter_names = ("eventFilterDroppedCount", "eventParserDroppedCount")
_drop_events_task_interval = 3600


class SyslogDaemon(PBDaemon):
    """
    Daemon for receiving SysLog events and recording them as Zenoss events.
    """

    mname = name = "zensyslog"

    _configservice = "Products.ZenHub.services.SyslogConfig"
    initialServices = PBDaemon.initialServices + [_configservice]

    def __init__(self, *args, **kwargs):
        super(SyslogDaemon, self).__init__(*args, **kwargs)

        self.configCycleInterval = 2 * 60  # seconds
        self.cycleInterval = 5 * 60  # seconds

        self._rules = FilterRules(self)
        self._event_filter = SyslogMsgFilter(self._rules, self.counters)
        provideUtility(self._event_filter, ICollectorEventTransformer)

        self._heartbeat_sender = ZenHubHeartbeatSender(
            self.options.monitor,
            self.name,
            self.options.heartbeatTimeout,
        )
        self._heartbeat_task = None

        self._parsers = Parsers(self.sendEvent)
        self._processor = SyslogProcessor(
            self.sendEvent,
            self.options.minpriority,
            self.options.parsehost,
            self.options.monitor,
            self._parsers,
        )
        self._loader = ConfigLoader(
            self.getRemoteConfigServiceProxy,
            self._parsers,
            self._processor,
            self._rules,
        )
        self._loader_task = None

        self._drop_events_task = None

        self._receiver = None

    def buildOptions(self):
        super(SyslogDaemon, self).buildOptions()
        try:
            SYSLOG_PORT = socket.getservbyname("syslog", "udp")
        except socket.error:
            SYSLOG_PORT = 514
        self.parser.add_option(
            "--parsehost",
            dest="parsehost",
            action="store_true",
            default=False,
            help="Try to parse the hostname part of a syslog HEADER",
        )
        self.parser.add_option(
            "--stats",
            dest="stats",
            action="store_true",
            default=False,
            help="Print statistics to log every 2 secs",
        )
        self.parser.add_option(
            "--logorig",
            dest="logorig",
            action="store_true",
            default=False,
            help="Log the original message",
        )
        self.parser.add_option(
            "--logformat",
            dest="logformat",
            default="human",
            help="Human-readable (/var/log/messages) or raw (wire)",
        )
        self.parser.add_option(
            "--minpriority",
            dest="minpriority",
            default=6,
            type="int",
            help="Minimum priority message that zensyslog will accept",
        )
        self.parser.add_option(
            "--syslogport",
            dest="syslogport",
            default=SYSLOG_PORT,
            type="int",
            help="Port number to use for syslog events",
        )
        self.parser.add_option(
            "--listenip",
            dest="listenip",
            default="0.0.0.0",  # noqa: S104
            help="IP address to listen on. Default is %default",
        )
        self.parser.add_option(
            "--useFileDescriptor",
            dest="useFileDescriptor",
            type="int",
            help="Read from an existing connection rather opening a new port.",
            default=None,
        )
        self.parser.add_option(
            "--noreverseLookup",
            dest="noreverseLookup",
            action="store_true",
            default=False,
            help="Don't convert the remote device's IP address to a hostname.",
        )

    # @override
    def run(self):
        if (
            not self.options.useFileDescriptor
            and self.options.syslogport < 1024
        ):
            self.log.info(
                "opening privileged port %s", self.options.syslogport
            )
            # Makes a call to zensocket here,
            # which performs an exec* so it never returns.
            self.openPrivilegedPort(
                "--listen",
                "--proto=udp",
                "--port=%s:%d"
                % (self.options.listenip, self.options.syslogport),
            )
            self.log.error("Failed to open privileged port")
            sys.exit(1)
        super(SyslogDaemon, self).run()

    # @override
    @defer.inlineCallbacks
    def connected(self):
        try:
            # initial config load
            yield self._loader.task()

            self._start_heartbeat_task()
            self._start_loader_task()
            self._start_drop_events_task()
            self._start_receiver()
        except Exception:
            self.log.exception("BOOM!")

    # @override
    def postStatisticsImpl(self):
        if self._receiver is None:
            return
        totalTime, totalEvents, maxTime = self._processor.stats.report()
        self.rrdStats.counter("events", totalEvents)

    @defer.inlineCallbacks
    def getRemoteConfigServiceProxy(self):
        """Return the remote configuration service proxy."""
        proxy = yield self.getService(self._configservice)
        defer.returnValue(proxy)

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

    def _start_loader_task(self):
        self._loader_task = LoopingCall(self._loader.task)
        self._loader_task.start(self.cycleInterval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_loader_task
        )
        self.log.info("started task to retrieve configuration data")

    def _stop_loader_task(self):
        if self._loader_task is None:
            return
        self._loader_task.stop()
        self._loader_task = None
        self.log.info("stopped task to retrieve configuration data")

    def _start_drop_events_task(self):
        self._drop_events_task = LoopingCall(self._send_drop_events)
        self._drop_events_task.start(_drop_events_task_interval)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_drop_events_task
        )
        self.log.info(
            "started task to send events with the count of dropped events"
        )

    def _stop_drop_events_task(self):
        if self._drop_events_task is None:
            return
        self._drop_events_task.stop()
        self._drop_events_task = None
        self.log.info(
            "stopped task to send events with the count of dropped events"
        )

    def _start_receiver(self):
        protocol = self._build_protocol()
        portfactory = self._build_port_factory()
        self._receiver = Receiver(protocol, portfactory)
        self._receiver.start()
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_receiver
        )
        reactor.addSystemEventTrigger(
            "after", "shutdown", self._displayStatistics
        )
        self.log.info("started receiving syslog messages")

    def _stop_receiver(self):
        if self._receiver is None:
            return
        self._receiver.stop()
        self._receiver = None
        self.log.info("stopped receiving syslog messages")

    def _build_protocol(self):
        if self.options.logorig:
            if self.options.logformat == "human":
                formatter = HumanFormatter()
            else:
                formatter = RawFormatter()
            logger = MessageLogger(formatter)
        else:
            logger = DropLogger()

        return SyslogProtocol(
            self._processor,
            logger,
            self.counters,
            self.options.noreverseLookup,
        )

    def _build_port_factory(self):
        if self.options.useFileDescriptor is not None:
            fd = int(self.options.useFileDescriptor)
            return AdoptPort(fd)
        return CreatePort(self.options.syslogport, self.options.listenip)

    def _send_drop_events(self):
        for name in _dropped_counter_names:
            count = self.counters[name]
            event = {
                "component": self.name,
                "device": self.options.monitor,
                "eventClass": "/App/Zenoss",
                "eventKey": "zensyslog.{}".format(name),
                "summary": "{}: {}".format(name, count),
                "severity": Info,
            }
            self.sendEvent(event)

    def _displayStatistics(self):
        totalTime, totalEvents, maxTime = self._processor.stats.report()
        display = "%d events processed in %.2f seconds" % (
            totalEvents,
            totalTime,
        )
        if totalEvents > 0:
            display += (
                "\n%.5f average seconds per event\n"
                "Maximum processing time for one event was %.5f\n"
            ) % ((totalTime / totalEvents), maxTime)
        return display
