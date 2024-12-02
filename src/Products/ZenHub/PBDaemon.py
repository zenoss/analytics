##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
import os
import sys

from itertools import chain
from urlparse import urlparse

import six

from twisted.cred.credentials import UsernamePassword
from twisted.internet.endpoints import clientFromString, serverFromString
from twisted.internet import defer, reactor, task
from twisted.internet.error import ReactorNotRunning
from twisted.spread import pb
from zope.component import provideUtility
from zope.interface import implementer

from Products.ZenEvents.ZenEventClasses import (
    App_Start,
    App_Stop,
    Clear,
    Warning,
)
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.MetricReporter import TwistedMetricReporter
from Products.ZenUtils.metricwriter import (
    AggregateMetricWriter,
    DerivativeTracker,
    FilteredMetricWriter,
    MetricWriter,
    ThresholdNotifier,
)
from Products.ZenUtils.Utils import importClass, lookupClass
from Products.ZenUtils.ZenDaemon import ZenDaemon

from .errors import HubDown, translateError
from .events import EventClient, EventQueueManager
from .interfaces import IEventService
from .localserver import LocalServer, ZenHubStatus
from .metricpublisher import publisher
from .pinger import PingZenHub
from .zenhubclient import ZenHubClient

PB_PORT = 8789

# field size limits for events
DEFAULT_LIMIT = 524288  # 512k
LIMITS = {"summary": 256, "message": 4096}

startEvent = {
    "eventClass": App_Start,
    "summary": "started",
    "severity": Clear,
}

stopEvent = {
    "eventClass": App_Stop,
    "summary": "stopped",
    "severity": Warning,
}

DEFAULT_HUB_HOST = "localhost"
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = "admin"
DEFAULT_HUB_PASSWORD = "zenoss"  # noqa S105
DEFAULT_HUB_MONITOR = "localhost"


class FakeRemote:
    def callRemote(self, *args, **kwargs):
        return defer.fail(HubDown())


@implementer(IEventService)
class PBDaemon(ZenDaemon, pb.Referenceable):
    """Base class for services that connect to ZenHub."""

    mname = name = "pbdaemon"

    initialServices = ["EventService"]

    _customexitcode = 0

    def __init__(
        self,
        noopts=0,
        keeproot=False,
        name=None,
        publisher=None,
        internal_publisher=None,
    ):
        # if we were provided our collector name via the constructor
        # instead of via code, be sure to store it correctly.
        if name is not None:
            self.name = self.mname = name

        provideUtility(self, IEventService)

        super(PBDaemon, self).__init__(noopts, keeproot)

        # Configure/initialize the ZenHub client
        self.__zhclient = _getZenHubClient(self, self.options)
        self.__zhclient.notify_on_connect(self._load_initial_services)
        self.__zenhub_ready = None

        self.__pinger = PingZenHub(self.__zhclient)

        self._thresholds = Thresholds()
        self._threshold_notifier = ThresholdNotifier(
            self.sendEvent, self._thresholds
        )

        self.rrdStats = DaemonStats()
        self.lastStats = 0
        self.counters = collections.Counter()

        self.startEvent = startEvent.copy()
        self.stopEvent = stopEvent.copy()
        details = {"component": self.name, "device": self.options.monitor}
        for evt in self.startEvent, self.stopEvent:
            evt.update(details)

        self._metrologyReporter = None
        self.__statistics_task = None

        self.__publisher = publisher
        self.__internal_publisher = internal_publisher
        self.__metric_writer = None
        self.__derivative_tracker = None

        self.__eventqueue = None
        self.__eventclient = None
        self.__recordQueuedEventsCountLoop = task.LoopingCall(
            self.__record_queued_events_count
        )

        if self.options.cycle:
            self.__server = _getLocalServer(self.options)
            self.__server.add_resource(
                "zenhub",
                ZenHubStatus(
                    lambda: (
                        "connected"
                        if self.__zenhub_connected
                        else "disconnected"
                    )
                ),
            )
        else:
            self.__server = None

        self.__zenhub_connected = False
        self.__zhclient.notify_on_connect(
            lambda: self._set_zenhub_connected(True)
        )

    def _set_zenhub_connected(self, state):
        self.__zenhub_connected = state
        if state:
            # Re-add the disconnect callback because the ZenHub client
            # removes all disconnect callbacks after a disconnect.
            self.__zhclient.notify_on_disconnect(
                lambda: self._set_zenhub_connected(False)
            )

    @property
    def local_server(self):
        return self.__server

    @property
    def services(self):
        return self.__zhclient.services

    def __record_queued_events_count(self):
        if self.rrdStats.name and self.__eventqueue is not None:
            self.rrdStats.gauge("eventQueueLength", len(self.__eventqueue))

    def generateEvent(self, event, **kw):
        """
        Return a 'filled out' version of the given event.
        """
        eventCopy = {}
        for k, v in chain(event.items(), kw.items()):
            if isinstance(v, six.string_types):
                # default max size is 512k
                size = LIMITS.get(k, DEFAULT_LIMIT)
                eventCopy[k] = v[0:size] if len(v) > size else v
            else:
                eventCopy[k] = v

        eventCopy["agent"] = self.name
        eventCopy["monitor"] = self.options.monitor
        eventCopy["manager"] = self.fqdn
        return eventCopy

    def publisher(self):
        if not self.__publisher:
            host, port = urlparse(self.options.redisUrl).netloc.split(":")
            try:
                port = int(port)
            except ValueError:
                self.log.exception(
                    "redis url contains non-integer port "
                    "value %s, defaulting to %s",
                    port,
                    publisher.defaultRedisPort,
                )
                port = publisher.defaultRedisPort
            self.__publisher = publisher.RedisListPublisher(
                host,
                port,
                self.options.metricBufferSize,
                channel=self.options.metricsChannel,
                maxOutstandingMetrics=self.options.maxOutstandingMetrics,
            )
        return self.__publisher

    def setInternalPublisher(self, publisher):
        self.__internal_publisher = publisher

    def internalPublisher(self):
        if not self.__internal_publisher:
            url = os.environ.get("CONTROLPLANE_CONSUMER_URL", None)
            username = os.environ.get("CONTROLPLANE_CONSUMER_USERNAME", "")
            password = os.environ.get("CONTROLPLANE_CONSUMER_PASSWORD", "")
            if url:
                self.__internal_publisher = publisher.HttpPostPublisher(
                    username, password, url
                )
        return self.__internal_publisher

    def metricWriter(self):
        if not self.__metric_writer:
            publisher = self.publisher()
            metric_writer = MetricWriter(publisher)
            if os.environ.get("CONTROLPLANE", "0") == "1":
                internal_publisher = self.internalPublisher()
                if internal_publisher:

                    def _check_internal(metric, value, timestamp, tags):
                        return tags and tags.get("internal", False)

                    internal_metric_writer = FilteredMetricWriter(
                        internal_publisher, _check_internal
                    )
                    self.__metric_writer = AggregateMetricWriter(
                        [metric_writer, internal_metric_writer]
                    )
            else:
                self.__metric_writer = metric_writer
        return self.__metric_writer

    def derivativeTracker(self):
        if not self.__derivative_tracker:
            self.__derivative_tracker = DerivativeTracker()
        return self.__derivative_tracker

    def eventService(self):
        return self.getServiceNow("EventService")

    def sendEvents(self, events):
        if self.__eventclient is None:
            return
        return self.__eventclient.sendEvents(events)

    def sendHeartbeat(self, event):
        if self.__eventclient is None:
            return
        self.__eventclient.sendHeartbeat(event)

    @defer.inlineCallbacks
    def sendEvent(self, event, **kw):
        if self.__eventclient is None:
            return
        yield self.__eventclient.sendEvent(event, **kw)

    def getServiceNow(self, svcName):
        svc = self.__zhclient.services.get(svcName)
        if svc is None:
            self.log.warning(
                "no service named %r: ZenHub may be disconnected", svcName
            )
        return svc or FakeRemote()

    @defer.inlineCallbacks
    def getService(self, name, serviceListeningInterface=None):
        """
        Attempt to get a service from ZenHub.

        @rtype: Deferred
        """
        svc = yield self.__zhclient.get_service(
            name,
            self.options.monitor,
            serviceListeningInterface or self,
            self.options.__dict__,
        )
        defer.returnValue(svc)

    def connect(self):
        self.__zenhub_ready = self.__zhclient.start()
        self.__pinger.start()
        return self.__zenhub_ready

    def connected(self):
        """
        Invoked after a ZenHub connection is established and the
        initial set of services have been loaded.

        Sub-classes should override this method to add their own
        functionality.

        @rtype: Deferred
        """

    def getThresholds(self):
        return self._thresholds

    def run(self):
        # Start the connection to zenhub
        self.connect()

        self.rrdStats.config(
            self.name,
            self.options.monitor,
            self.metricWriter(),
            self._threshold_notifier,
            self.derivativeTracker(),
        )

        if self.options.cycle:
            self.__server.start()
            reactor.addSystemEventTrigger(
                "before", "shutdown", self.__server.stop
            )

        reactor.addSystemEventTrigger(
            "after",
            "shutdown",
            lambda: self.log.info("%s shutting down", self.name),
        )

        reactor.callWhenRunning(self._started)
        reactor.run()
        if self._customexitcode:
            sys.exit(self._customexitcode)

    def setExitCode(self, exitcode):
        self._customexitcode = exitcode

    def stop(self, ignored=""):
        if reactor.running:
            try:
                reactor.stop()
            except ReactorNotRunning:
                self.log.debug("tried to stop reactor that was stopped")
        else:
            self.log.debug("stop() called when not running")

    _started_failures = {
        "connect": "failed to connect to ZenHub",
        "services": "failed to retrieve a service from ZenHub",
        "eventclient": "failed to configure and start the event client",
        "stats": "failed to configure and start statistics recording",
    }

    @defer.inlineCallbacks
    def _load_initial_services(self):
        msg = self._started_failures["services"]
        try:
            for svcname in self.initialServices:
                try:
                    yield self.getService(svcname)
                except Exception:
                    if self.options.cycle:
                        self.log.exception(msg)
                    else:
                        raise
                else:
                    self.log.info("retrieved ZenHub service  name=%s", svcname)
            self.log.info("finished retrieving initial services")
        except Exception as ex:
            if self.options.cycle:
                self.log.exception(msg)
            else:
                detail = ("%s %s" % (type(ex).__name__, ex)).strip()
                self.log.critical("%s: %s", msg, detail)
                self.stop()

    @defer.inlineCallbacks
    def _started(self):
        # Called when the Twisted reactor is running.
        try:
            # Wait for the connection to zenhub
            state = "connect"
            self.log.info("waiting for zenhub")
            ready, self.__zenhub_ready = self.__zenhub_ready, None
            yield ready

            state = "eventclient"
            self._setup_event_client()

            if self.options.cycle:
                state = "stats"
                self._start_statistics_task()

                state = "metrics"
                self._start_internal_metrics_task()

            reactor.addSystemEventTrigger("before", "shutdown", self._stop)

            # Schedule the `connected` method to run
            reactor.callLater(0, self.connected)
        except Exception as ex:
            msg = self._started_failures[state]
            if self.options.cycle:
                self.log.exception(msg)
            else:
                detail = ("%s %s" % (type(ex).__name__, ex)).strip()
                self.log.critical("%s: %s", msg, detail)
            self.stop()

    @defer.inlineCallbacks
    def _stop(self):
        if self.__eventclient is not None:
            self.__eventclient.sendEvent(self.stopEvent)
            yield self.__eventclient.stop()
            self.log.debug("stopped event client")
        yield self.__zhclient.stop()

    def _setup_event_client(self):
        self.__eventqueue = EventQueueManager(self.options, self.log)
        self.__eventclient = EventClient(
            self.options,
            self.__eventqueue,
            self.generateEvent,
            lambda: self.getService("EventService"),
        )
        self.__eventclient.start()
        self.__eventclient.sendEvent(self.startEvent)
        self.__recordQueuedEventsCountLoop.start(2.0, now=False)
        self.log.info("started event client")

    def _start_internal_metrics_task(self):
        self._metrologyReporter = TwistedMetricReporter(
            self.options.writeStatistics,
            self.metricWriter(),
            {
                "zenoss_daemon": self.name,
                "zenoss_monitor": self.options.monitor,
                "internal": True,
            },
        )
        self._metrologyReporter.start()
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_internal_metrics_task
        )
        self.log.info("started internal metrics task")

    def _stop_internal_metrics_task(self):
        if self._metrologyReporter:
            self._metrologyReporter.stop()
            self._metrologyReporter = None
            self.log.info("stopped internal metrics task")

    def _start_statistics_task(self):
        self.__statistics_task = task.LoopingCall(self.postStatistics)
        self.__statistics_task.start(self.options.writeStatistics, now=False)
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._stop_statistics_task
        )
        self.log.info("started statistics reporting task")

    def _stop_statistics_task(self):
        if self.__statistics_task:
            self.__statistics_task.stop()
            self.__statistics_task = None
            self.log.info("stopped statistics reporting task")

    def postStatisticsImpl(self):
        pass

    def postStatistics(self):
        # save daemon counter stats
        for name, value in chain(
            self.counters.items(), self.__eventclient.counters.items()
        ):
            self.log.debug("counter %s, value %d", name, value)
            self.rrdStats.counter(name, value)

        # persist counters values
        try:
            self.postStatisticsImpl()
        except Exception:
            self.log.exception("sub-class postStatisticsImpl method failed")

    def _pickleName(self):
        instance_id = os.environ.get("CONTROLPLANE_INSTANCE_ID")
        return "var/%s_%s_counters.pickle" % (self.name, instance_id)

    def remote_getName(self):
        return self.name

    def remote_shutdown(self, unused):
        self.stop()
        self.sigTerm()

    def remote_setPropertyItems(self, items):
        pass

    @translateError
    def remote_updateThresholdClasses(self, classes):
        self.loadThresholdClasses(classes)

    def loadThresholdClasses(self, classnames):
        for name in classnames:
            try:
                cls = lookupClass(name)
                if cls:
                    self.log.debug(
                        "already imported threshold class  class=%s", name
                    )
                    continue
                importClass(name)
                self.log.info("imported threshold class  class=%s", name)
            except ImportError:
                self.log.exception("unable to import threshold class %s", name)
            except AttributeError:
                self.log.exception("unable to import threshold class %s", name)

    def buildOptions(self):
        super(PBDaemon, self).buildOptions()
        LocalServer.buildOptions(self.parser)
        self.parser.add_option(
            "--hubhost",
            dest="hubhost",
            default=DEFAULT_HUB_HOST,
            help="Host of zenhub daemon; default %default",
        )
        self.parser.add_option(
            "--hubport",
            dest="hubport",
            type="int",
            default=DEFAULT_HUB_PORT,
            help="Port zenhub listens on; default %default",
        )
        self.parser.add_option(
            "--hubusername",
            dest="hubusername",
            default=DEFAULT_HUB_USERNAME,
            help="Username for zenhub login; default %default",
        )
        self.parser.add_option(
            "--hubpassword",
            dest="hubpassword",
            default=DEFAULT_HUB_PASSWORD,
            help="Password for zenhub login; default %default",
        )
        self.parser.add_option(
            "--monitor",
            dest="monitor",
            default=DEFAULT_HUB_MONITOR,
            help="Name of monitor instance to use for"
            " configuration; default %default",
        )
        self.parser.add_option(
            "--initialHubTimeout",
            dest="hubtimeout",
            type="int",
            default=30,
            help="Initial time to wait for a ZenHub connection",
        )
        self.parser.add_option(
            "--zenhubpinginterval",
            dest="zhPingInterval",
            default=120,
            type="int",
            help="How often to ping zenhub",
        )

        self.parser.add_option(
            "--allowduplicateclears",
            dest="allowduplicateclears",
            default=False,
            action="store_true",
            help="Send clear events even when the most "
            "recent event was also a clear event.",
        )
        self.parser.add_option(
            "--duplicateclearinterval",
            dest="duplicateclearinterval",
            default=0,
            type="int",
            help="Send a clear event every DUPLICATECLEARINTEVAL events.",
        )
        self.parser.add_option(
            "--eventflushseconds",
            dest="eventflushseconds",
            default=5.0,
            type="float",
            help="Seconds between attempts to flush events to ZenHub.",
        )
        self.parser.add_option(
            "--eventflushchunksize",
            dest="eventflushchunksize",
            default=50,
            type="int",
            help="Number of events to send to ZenHub at one time",
        )
        self.parser.add_option(
            "--maxqueuelen",
            dest="maxqueuelen",
            default=5000,
            type="int",
            help="Maximum number of events to queue",
        )
        self.parser.add_option(
            "--queuehighwatermark",
            dest="queueHighWaterMark",
            default=0.75,
            type="float",
            help="The size, in percent, of the event queue "
            "when event pushback starts",
        )
        self.parser.add_option(
            "--disable-event-deduplication",
            dest="deduplicate_events",
            default=True,
            action="store_false",
            help="Disable event de-duplication",
        )

        self.parser.add_option(
            "--redis-url",
            dest="redisUrl",
            type="string",
            default="redis://localhost:{default}/0".format(
                default=publisher.defaultRedisPort
            ),
            help="redis connection string: "
            "redis://[hostname]:[port]/[db]; default: %default",
        )
        self.parser.add_option(
            "--metricBufferSize",
            dest="metricBufferSize",
            type="int",
            default=publisher.defaultMetricBufferSize,
            help="Number of metrics to buffer if redis goes down",
        )
        self.parser.add_option(
            "--metricsChannel",
            dest="metricsChannel",
            type="string",
            default=publisher.defaultMetricsChannel,
            help="redis channel to which metrics are published",
        )
        self.parser.add_option(
            "--maxOutstandingMetrics",
            dest="maxOutstandingMetrics",
            type="int",
            default=publisher.defaultMaxOutstandingMetrics,
            help="Max Number of metrics to allow in redis",
        )
        self.parser.add_option(
            "--writeStatistics",
            dest="writeStatistics",
            type="int",
            default=30,
            help="How often to write internal statistics value in seconds",
        )

        self.parser.add_option(
            "--disable-ping-perspective",
            dest="pingPerspective",
            default=True,
            action="store_false",
            help="Enable or disable ping perspective",
        )


def _getZenHubClient(app, options):
    creds = UsernamePassword(options.hubusername, options.hubpassword)
    endpointDescriptor = "tcp:{host}:{port}".format(
        host=options.hubhost, port=options.hubport
    )
    endpoint = clientFromString(reactor, endpointDescriptor)
    return ZenHubClient(
        app,
        endpoint,
        creds,
        options.hubtimeout,
        reactor,
    )


def _getLocalServer(options):
    # bind the server to the localhost interface so only local
    # connections can be established.
    server_endpoint_descriptor = "tcp:{port}:interface=127.0.0.1".format(
        port=options.localport
    )
    server_endpoint = serverFromString(reactor, server_endpoint_descriptor)
    return LocalServer(reactor, server_endpoint)
