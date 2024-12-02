import logging
import sys

from unittest import TestCase
from mock import ANY, Mock, patch, create_autospec, call

# Breaks Test Isolation. Products/ZenHub/metricpublisher/utils.py:15
# ImportError: No module named eventlet
from Products.ZenHub.PBDaemon import (
    collections,
    defer,
    PBDaemon,
    publisher,
)

PATH = {"src": "Products.ZenHub.PBDaemon"}


class PBDaemonClassTest(TestCase):
    """ """

    def test_class_attributes(t):
        t.assertEqual(PBDaemon.name, "pbdaemon")
        t.assertEqual(PBDaemon.initialServices, ["EventService"])
        t.assertEqual(PBDaemon._customexitcode, 0)


class PBDaemonInitTest(TestCase):
    @patch("{src}.sys".format(**PATH), autospec=True)
    @patch("{src}.task.LoopingCall".format(**PATH), autospec=True)
    @patch("{src}.stopEvent".format(**PATH), name="stopEvent", autospec=True)
    @patch("{src}.startEvent".format(**PATH), name="startEvent", autospec=True)
    @patch("{src}.DaemonStats".format(**PATH), autospec=True)
    @patch("{src}.EventQueueManager".format(**PATH), autospec=True)
    @patch("{src}.ZenDaemon.__init__".format(**PATH), autospec=True)
    @patch("{src}._getLocalServer".format(**PATH), autospec=True)
    @patch("{src}._getZenHubClient".format(**PATH), autospec=True)
    @patch("{src}.Thresholds".format(**PATH), autospec=True)
    @patch("{src}.ThresholdNotifier".format(**PATH), autospec=True)
    def test___init__(
        t,
        ThresholdNotifier,
        Thresholds,
        _getZenHubClient,
        _getLocalServer,
        ZenDaemon_init,
        EventQueueManager,
        DaemonStats,
        startEvent,
        stopEvent,
        LoopingCall,
        sys,
    ):
        noopts = (0,)
        keeproot = False
        name = "pb_init"

        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.pbdaemon_patchers = [
            patch.object(PBDaemon, "options", create=True),
            patch.object(PBDaemon, "log", create=True),
        ]
        for patcher in t.pbdaemon_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        pbd = PBDaemon(noopts=noopts, keeproot=keeproot, name=name)

        # runs parent class init
        # this should really be using super(
        ZenDaemon_init.assert_called_with(pbd, noopts, keeproot)

        t.assertEqual(pbd.name, name)
        t.assertEqual(pbd.mname, name)

        zhc = _getZenHubClient.return_value
        zhc.notify_on_connect.assert_has_calls(
            [call(pbd._load_initial_services), call(ANY)]
        )

        ls = _getLocalServer.return_value
        ls.add_resource.assert_called_once_with("zenhub", ANY)

        EventQueueManager.assert_not_called()

        # Check lots of attributes, should verify that they are needed
        t.assertEqual(pbd._thresholds, Thresholds.return_value)
        t.assertEqual(pbd._threshold_notifier, ThresholdNotifier.return_value)
        t.assertEqual(pbd.rrdStats, DaemonStats.return_value)
        t.assertEqual(pbd.lastStats, 0)
        t.assertEqual(pbd.services, _getZenHubClient.return_value.services)
        t.assertEqual(pbd.startEvent, startEvent.copy())
        t.assertEqual(pbd.stopEvent, stopEvent.copy())

        # appends name and device to start, stop, and heartbeat events
        details = {"component": name, "device": PBDaemon.options.monitor}
        pbd.startEvent.update.assert_called_with(details)
        pbd.stopEvent.update.assert_called_with(details)

        # more attributes
        t.assertIsInstance(pbd.counters, collections.Counter)
        t.assertEqual(pbd._metrologyReporter, None)

    @patch("{src}.ZenDaemon.__init__".format(**PATH), side_effect=IOError)
    def test__init__exit_on_ZenDaemon_IOError(t, ZenDaemon):
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        log_patcher = patch.object(PBDaemon, "log", create=True)
        log_patcher.start()
        t.addCleanup(log_patcher.stop)

        with t.assertRaises(IOError):
            PBDaemon()

    def test_buildOptions(t):
        """After initialization, the PBDaemon instance should have
        options parsed from its buildOptions method
        assertions based on default options

        Patch PBDaemon's __init__, because CmdBase will override config
        settings with values from the global.conf file
        """
        init_patcher = patch.object(
            PBDaemon, "__init__", autospec=True, return_value=None
        )
        init_patcher.start()
        t.addCleanup(init_patcher.stop)

        pbd = PBDaemon()
        pbd.parser = None
        pbd.usage = "%prog [options]"
        pbd.noopts = True
        pbd.inputArgs = None

        # Given no commandline options
        sys.argv = []
        pbd.buildOptions()
        pbd.parseOptions()

        from Products.ZenHub.PBDaemon import (
            DEFAULT_HUB_HOST,
            DEFAULT_HUB_PORT,
            DEFAULT_HUB_USERNAME,
            DEFAULT_HUB_PASSWORD,
            DEFAULT_HUB_MONITOR,
        )

        t.assertEqual(pbd.options.hubhost, DEFAULT_HUB_HOST)  # No default
        t.assertEqual(pbd.options.hubport, DEFAULT_HUB_PORT)
        t.assertEqual(pbd.options.hubusername, DEFAULT_HUB_USERNAME)
        t.assertEqual(pbd.options.hubpassword, DEFAULT_HUB_PASSWORD)
        t.assertEqual(pbd.options.monitor, DEFAULT_HUB_MONITOR)
        t.assertEqual(pbd.options.hubtimeout, 30)
        t.assertEqual(pbd.options.allowduplicateclears, False)
        t.assertEqual(pbd.options.duplicateclearinterval, 0)
        t.assertEqual(pbd.options.eventflushseconds, 5)
        t.assertEqual(pbd.options.eventflushseconds, 5.0)
        t.assertEqual(pbd.options.eventflushchunksize, 50)
        t.assertEqual(pbd.options.maxqueuelen, 5000)
        t.assertEqual(pbd.options.queueHighWaterMark, 0.75)
        t.assertEqual(pbd.options.zhPingInterval, 120)
        t.assertEqual(pbd.options.deduplicate_events, True)
        t.assertEqual(
            pbd.options.redisUrl,
            "redis://localhost:{default}/0".format(
                default=publisher.defaultRedisPort
            ),
        )
        t.assertEqual(
            pbd.options.metricBufferSize, publisher.defaultMetricBufferSize
        )
        t.assertEqual(
            pbd.options.metricsChannel, publisher.defaultMetricsChannel
        )
        t.assertEqual(
            pbd.options.maxOutstandingMetrics,
            publisher.defaultMaxOutstandingMetrics,
        )
        t.assertEqual(pbd.options.pingPerspective, True)
        t.assertEqual(pbd.options.writeStatistics, 30)


class PBDaemonTest(TestCase):
    def setUp(t):
        # Patch external dependencies
        # current version touches the reactor directly
        patches = [
            "_getZenHubClient",
            "EventClient",
            "EventQueueManager",
            "LocalServer",
            "MetricWriter",
            "publisher",
            "reactor",
        ]

        for target in patches:
            patcher = patch("{src}.{}".format(target, **PATH), spec=True)
            setattr(t, target, patcher.start())
            t.addCleanup(patcher.stop)

        t.EventClient.counters = Mock(collections.Counter(), autospec=True)

        # Required commandline options
        sys.argv = [
            "Start",
        ]

        t.name = "pb_daemon_name"
        t.pbd = PBDaemon(name=t.name)
        t.pbd.fqdn = "fqdn"

        # Mock out 'log' to prevent spurious output to stdout.
        t.pbd.log = Mock(spec=logging.getLoggerClass())

    def test_publisher(t):
        host = "localhost"
        port = 9999
        t.pbd.options.redisUrl = "http://{}:{}".format(host, port)

        ret = t.pbd.publisher()

        t.assertEqual(ret, t.publisher.RedisListPublisher.return_value)
        t.publisher.RedisListPublisher.assert_called_with(
            host,
            port,
            t.pbd.options.metricBufferSize,
            channel=t.pbd.options.metricsChannel,
            maxOutstandingMetrics=t.pbd.options.maxOutstandingMetrics,
        )

    @patch("{src}.os".format(**PATH), autospec=True)
    def test_internalPublisher(t, _os):
        # All the methods with this pattern need to be converted to properties
        url = Mock(name="url", spec_set=[])
        username = "username"
        password = "password"  # noqa S105
        _os.environ = {
            "CONTROLPLANE_CONSUMER_URL": url,
            "CONTROLPLANE_CONSUMER_USERNAME": username,
            "CONTROLPLANE_CONSUMER_PASSWORD": password,
        }

        ret = t.pbd.internalPublisher()

        t.assertEqual(ret, t.publisher.HttpPostPublisher.return_value)
        t.publisher.HttpPostPublisher.assert_called_with(
            username,
            password,
            url,
        )
        t.assertEqual(t.pbd.internalPublisher(), ret)

    @patch("{src}.os".format(**PATH), autospec=True)
    def test_metricWriter_legacy(t, _os):
        t.pbd.publisher = create_autospec(t.pbd.publisher)
        t.pbd.internalPublisher = create_autospec(t.pbd.internalPublisher)
        _os.environ = {"CONTROLPLANE": "0"}

        ret = t.pbd.metricWriter()

        t.MetricWriter.assert_called_with(t.pbd.publisher())
        t.assertEqual(ret, t.MetricWriter.return_value)
        t.assertEqual(t.pbd.metricWriter(), ret)

    @patch("{src}.AggregateMetricWriter".format(**PATH), autospec=True)
    @patch("{src}.FilteredMetricWriter".format(**PATH), autospec=True)
    @patch("{src}.os".format(**PATH), autospec=True)
    def test_metricWriter_controlplane(
        t, _os, _FilteredMetricWriter, _AggregateMetricWriter
    ):
        t.pbd.publisher = create_autospec(t.pbd.publisher, name="publisher")
        t.pbd.internalPublisher = create_autospec(
            t.pbd.internalPublisher, name="internalPublisher"
        )
        _os.environ = {"CONTROLPLANE": "1"}

        ret = t.pbd.metricWriter()

        t.MetricWriter.assert_called_with(t.pbd.publisher())
        _AggregateMetricWriter.assert_called_with(
            [t.MetricWriter.return_value, _FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, _AggregateMetricWriter.return_value)
        t.assertEqual(t.pbd.metricWriter(), ret)

    @patch("{src}.DerivativeTracker".format(**PATH), autospec=True)
    def test_derivativeTracker(t, _DerivativeTracker):
        ret = t.pbd.derivativeTracker()

        t.assertEqual(ret, _DerivativeTracker.return_value)

    def test_connect(t):
        zhc = t._getZenHubClient.return_value
        expected = zhc.start.return_value
        ret = t.pbd.connect()
        t.assertEqual(ret, expected)

    def test_eventService(t):
        # alias for getServiceNow
        t.pbd.getServiceNow = create_autospec(t.pbd.getServiceNow)
        t.pbd.eventService()
        t.pbd.getServiceNow.assert_called_with("EventService")

    def test_getServiceNow(t):
        svc_name = "svc_name"
        zhc = t._getZenHubClient.return_value
        zhc.services = {svc_name: "some service"}
        ret = t.pbd.getServiceNow(svc_name)
        t.assertEqual(ret, t.pbd.services[svc_name])

    @patch("{src}.FakeRemote".format(**PATH), autospec=True)
    def test_getServiceNow_FakeRemote_on_missing_service(t, FakeRemote):
        svc_name = "svc_name"
        zhc = t._getZenHubClient.return_value
        zhc.services = {}

        ret = t.pbd.getServiceNow(svc_name)
        t.assertEqual(ret, FakeRemote.return_value)

    def test_getService_known_service(t):
        zhc = t._getZenHubClient.return_value
        t.pbd.services["known_service"] = "service"
        ret = t.pbd.getService("known_service")

        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, zhc.get_service.return_value)

    def test_getService(t):
        """this is going to be ugly to test,
        and badly needs to be rewritten as an inlineCallback
        """
        zhc = t._getZenHubClient.return_value
        serviceListeningInterface = object()
        service_name = "service_name"

        actual = t.pbd.getService(service_name, serviceListeningInterface)

        t.assertIsInstance(actual, defer.Deferred)
        t.assertEqual(actual.result, zhc.get_service.return_value)
        zhc.get_service.assert_has_calls(
            [
                call(
                    service_name,
                    t.pbd.options.monitor,
                    serviceListeningInterface,
                    t.pbd.options.__dict__,
                )
            ]
        )

    def test__load_initial_services(t):  # , defer):
        """execute getService(svc_name) for every service in initialServices
        in parallel deferreds
        """
        getService = Mock(name="getService")
        t.pbd.getService = getService

        t.pbd._load_initial_services()

        getService.assert_has_calls(
            [call(svcname) for svcname in t.pbd.initialServices]
        )

    def test_connected(t):
        # does nothing
        t.pbd.connected()

    @patch("{src}.sys".format(**PATH), autospec=True)
    @patch("{src}.task".format(**PATH), autospec=True)
    @patch("{src}.TwistedMetricReporter".format(**PATH), autospec=True)
    def test_run(t, _TwistedMetricReporter, _task, _sys):
        """Starts up all of the internal loops,
        does not return until reactor.run() completes (reactor is shutdown)
        """
        t.pbd.rrdStats = Mock(spec_set=t.pbd.rrdStats)
        t.pbd.connect = create_autospec(t.pbd.connect)
        t.pbd._customexitcode = 99
        t.pbd.options = Mock(name="options", cycle=True)
        t.pbd._PBDaemon__server = Mock()
        host = "localhost"
        port = 9999
        t.pbd.options.redisUrl = "http://{}:{}".format(host, port)

        t.pbd.run()

        t.pbd.connect.assert_called_with()

        t.pbd.rrdStats.config.assert_called_with(
            t.pbd.name,
            t.pbd.options.monitor,
            t.pbd.metricWriter(),
            t.pbd._threshold_notifier,
            t.pbd.derivativeTracker(),
        )

        t.reactor.callWhenRunning.assert_called_with(t.pbd._started)
        t.reactor.run.assert_called_with()

        # only calls sys.exit if a custom exitcode is set, should probably
        # exit even if exitcode = 0
        _sys.exit.assert_called_with(t.pbd._customexitcode)

    def test_setExitCode(t):
        exitcode = Mock()
        t.pbd.setExitCode(exitcode)
        t.assertEqual(t.pbd._customexitcode, exitcode)

    def test_stop(t):
        # stops the reactor and handles ReactorNotRunning
        t.reactor.running = True
        t.pbd.stop()
        t.reactor.stop.assert_called_with()

    def test_sendEvents(t):
        ec = t.EventClient.return_value
        t.pbd._setup_event_client()
        events = [{"name": "evt_a"}, {"name": "evt_b"}]

        d = t.pbd.sendEvents(events)

        t.assertEqual(d, ec.sendEvents.return_value)
        ec.sendEvents.assert_called_with(events)

    def test_sendEvent(t):
        ec = t.EventClient.return_value
        sendEvent = Mock(name="sendEvent")
        ec.sendEvent = sendEvent
        t.pbd._setup_event_client()
        event = {"name": "event"}

        d = t.pbd.sendEvent(event, newkey="newkey")

        t.assertIsInstance(d, defer.Deferred)
        t.assertIsNone(d.result)
        sendEvent.assert_has_calls([call(event, newkey="newkey")])

    def test_generateEvent(t):
        # returns a dict with keyword args, and other values added
        event = {"name": "event"}

        ret = t.pbd.generateEvent(event, newkey="newkey")

        t.assertEqual(
            ret,
            {
                "name": "event",
                "newkey": "newkey",
                "agent": t.pbd.name,
                "manager": t.pbd.fqdn,
                "monitor": t.pbd.options.monitor,
            },
        )

    def test_postStatisticsImpl(t):
        # does nothing, maybe implemented by subclasses
        t.pbd.postStatisticsImpl()

    def test_postStatistics(t):
        ec = t.EventClient.return_value
        ec.counters = collections.Counter()
        t.pbd._setup_event_client()
        # sets rrdStats, then calls postStatisticsImpl
        t.pbd.rrdStats = Mock(name="rrdStats", spec_set=["counter"])
        ctrs = {"c1": 3, "c2": 5}
        for k, v in ctrs.items():
            t.pbd.counters[k] = v

        t.pbd.postStatistics()

        t.pbd.rrdStats.counter.assert_has_calls(
            [call(k, v) for k, v in ctrs.items()]
        )

    @patch("{src}.os".format(**PATH))
    def test__pickleName(t, _os):
        # refactor as a property
        ret = t.pbd._pickleName()
        _os.environ.get.assert_called_with("CONTROLPLANE_INSTANCE_ID")
        t.assertEqual(
            ret,
            "var/{}_{}_counters.pickle".format(
                t.pbd.name, _os.environ.get.return_value
            ),
        )

    def test_remote_getName(t):
        ret = t.pbd.remote_getName()
        t.assertEqual(ret, t.pbd.name)

    def test_remote_shutdown(t):
        t.pbd.stop = create_autospec(t.pbd.stop, name="stop")
        t.pbd.sigTerm = create_autospec(t.pbd.sigTerm, name="sigTerm")

        t.pbd.remote_shutdown("unused arg is ignored")

        t.pbd.stop.assert_called_with()
        t.pbd.sigTerm.assert_called_with()

    def test_remote_setPropertyItems(t):
        # does nothing
        t.pbd.remote_setPropertyItems("items arg is ignored")
