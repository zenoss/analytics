##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys

from mock import Mock, patch, create_autospec, call, sentinel
from unittest import TestCase

from zope.component import adaptedBy
from zope.interface.verify import verifyObject

from Products.ZenHub import XML_RPC_PORT, PB_PORT
from Products.ZenHub.zenhub import (
    DefaultConfProvider,
    DefaultHubHeartBeatCheck,
    HubCreatedEvent,
    HubWillBeCreatedEvent,
    IEventPublisher,
    IHubConfProvider,
    IHubCreatedEvent,
    IHubHeartBeatCheck,
    IHubServerConfig,
    IHubWillBeCreatedEvent,
    IMetricManager,
    initServiceManager,
    IParserReadyForOptionsEvent,
    ParserReadyForOptionsEvent,
    QUEUEMESSAGING_MODULE,
    reactor,
    report_reactor_delayed_calls,
    server_config,
    ServerConfig,
    stop_server,
    ZCmdBase,
    ZenHub,
    ZENHUB_MODULE,
)

PATH = {"src": "Products.ZenHub.zenhub"}


class ZenHubInitTest(TestCase):
    """Test zenhub.ZenHub.__init__ method."""

    @patch("{src}.register_legacy_worklist_metrics".format(**PATH))
    @patch("{src}.provideUtility".format(**PATH))
    @patch("{src}.InvalidationManager".format(**PATH))
    @patch("{src}.MetricManager".format(**PATH), autospec=True)
    @patch("{src}.StatsMonitor".format(**PATH), autospec=True)
    @patch("{src}.ZenHubStatusReporter".format(**PATH), autospec=True)
    @patch("{src}.make_pools".format(**PATH), autospec=True)
    @patch("{src}.make_service_manager".format(**PATH), autospec=True)
    @patch("{src}.getCredentialCheckers".format(**PATH), autospec=True)
    @patch("{src}.make_server_factory".format(**PATH), autospec=True)
    @patch("{src}.XmlRpcManager".format(**PATH), autospec=True)
    @patch("{src}.load_config_override".format(**PATH), spec=True)
    @patch("{src}.signal".format(**PATH), spec=True)
    @patch("{src}.App_Start".format(**PATH), spec=True)
    @patch("{src}.HubCreatedEvent".format(**PATH), spec=True)
    @patch("{src}.zenPath".format(**PATH), spec=True)
    @patch("{src}.reactor".format(**PATH), spec=True)
    @patch("{src}.ContinuousProfiler".format(**PATH), spec=True)
    @patch("{src}.HubWillBeCreatedEvent".format(**PATH), spec=True)
    @patch("{src}.notify".format(**PATH), spec=True)
    @patch("{src}.load_config".format(**PATH), spec=True)
    @patch("__builtin__.super".format(**PATH), autospec=True)
    @patch("{src}.initServiceManager".format(**PATH))
    def test___init__(
        t,
        initServiceManager,
        _super,
        load_config,
        notify,
        HubWillBeCreatedEvent,
        ContinuousProfiler,
        reactor,
        zenPath,
        HubCreatedEvent,
        App_Start,
        signal,
        load_config_override,
        XmlRpcManager,
        make_server_factory,
        getCredentialCheckers,
        make_service_manager,
        make_pools,
        ZenHubStatusReporter,
        StatsMonitor,
        MetricManager,
        InvalidationManager,
        provideUtility,
        register_legacy_worklist_metrics,
    ):
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.zenhub_patchers = [
            patch.object(ZenHub, "dmd", create=True),
            patch.object(ZenHub, "log", create=True),
            patch.object(ZenHub, "options", create=True),
            patch.object(ZenHub, "getRRDStats", autospec=True),
            patch.object(ZenHub, "_getConf", autospec=True),
            patch.object(ZenHub, "sendEvent", autospec=True),
            patch.object(ZenHub, "storage", create=True),
        ]

        for patcher in t.zenhub_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        ZenHub._getConf.return_value.id = "config_id"
        ZenHub.storage.mock_add_spec(["poll_invalidations"])

        zh = ZenHub()

        t.assertIsInstance(zh, ZenHub)
        # Skip Metrology validation for now due to complexity
        _super.return_value.__init__assert_called_with(ZenHub, zh)
        load_config.assert_called_with("hub.zcml", ZENHUB_MODULE)
        HubWillBeCreatedEvent.assert_called_with(zh)
        notify.assert_has_calls([call(HubWillBeCreatedEvent.return_value)])
        # Performance Profiling
        ContinuousProfiler.assert_called_with("zenhub", log=zh.log)
        zh.profiler.start.assert_called_with()

        # 'counters' is a ZenHub API.
        t.assertIs(zh.counters, StatsMonitor.return_value.counters)

        t.assertIsInstance(zh.shutdown, bool)
        t.assertFalse(zh.shutdown)

        t.assertIs(zh._monitor, StatsMonitor.return_value)
        t.assertIs(zh._status_reporter, ZenHubStatusReporter.return_value)
        t.assertIs(zh._pools, make_pools.return_value)
        t.assertIs(zh._service_manager, make_service_manager.return_value)
        t.assertIs(zh._server_factory, make_server_factory.return_value)
        t.assertIs(zh._xmlrpc_manager, XmlRpcManager.return_value)
        register_legacy_worklist_metrics.assert_called_once_with()

        # Event Handler shortcut
        t.assertEqual(zh.zem, zh.dmd.ZenEventManager)

        # Messaging config, including work and invalidations
        # Patched internal import of Products.ZenMessaging.queuemessaging
        load_config_override.assert_called_with(
            "twistedpublisher.zcml",
            QUEUEMESSAGING_MODULE,
        )
        HubCreatedEvent.assert_called_with(zh)
        notify.assert_called_with(HubCreatedEvent.return_value)
        zh.sendEvent.assert_called_with(
            zh,
            eventClass=App_Start,
            summary="zenhub started",
            severity=0,
        )

        StatsMonitor.assert_called_once_with()
        ZenHubStatusReporter.assert_called_once_with(
            StatsMonitor.return_value,
        )
        make_pools.assert_called_once_with()
        make_service_manager.assert_called_once_with(make_pools.return_value)
        getCredentialCheckers.assert_called_once_with(
            zh.options.passwordfile,
        )
        make_server_factory.assert_called_once_with(
            make_pools.return_value,
            make_service_manager.return_value,
            getCredentialCheckers.return_value,
        )
        XmlRpcManager.assert_called_once_with(
            zh.dmd,
            getCredentialCheckers.return_value[0],
        )

        MetricManager.assert_called_with(
            daemon_tags={
                "zenoss_daemon": "zenhub",
                "zenoss_monitor": zh.options.monitor,
                "internal": True,
            },
        )
        t.assertEqual(zh._metric_manager, MetricManager.return_value)
        t.assertEqual(
            zh._invalidation_manager,
            InvalidationManager.return_value,
        )
        provideUtility.assert_called_once_with(zh._metric_manager)

        signal.signal.assert_called_with(signal.SIGUSR2, zh.sighandler_USR2)

        initServiceManager.assert_called_once_with(zh.options)

    def test_PbRegistration(t):
        from twisted.spread.jelly import unjellyableRegistry

        t.assertIn("DataMaps.ObjectMap", unjellyableRegistry)
        t.assertIn(
            "Products.DataCollector.plugins.DataMaps.ObjectMap",
            unjellyableRegistry,
        )


class ZenHubTest(TestCase):
    """Test the zenhub.ZenHub class."""

    def setUp(t):
        # Patch out the ZenHub __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            ZCmdBase,
            "__init__",
            autospec=True,
            return_value=None,
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        # Mock out attributes set by ZCmdBase
        t.zcmdbase_patchers = [
            patch.object(ZenHub, "dmd", create=True),
            patch.object(ZenHub, "log", create=True),
            patch.object(ZenHub, "options", create=True),
            patch.object(ZenHub, "niceDoggie", create=True),
            patch.object(
                ZenHub,
                "storage",
                create=True,
                set_spec=["poll_invalidations"],
            ),
        ]
        for patcher in t.zcmdbase_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        # Patch external dependencies
        needs_patching = [
            "reactor",
            "XmlRpcManager",
            "make_server_factory",
            "getCredentialCheckers",
            "make_service_manager",
            "make_pools",
            "ZenHubStatusReporter",
            "StatsMonitor",
            "InvalidationManager",
            "MetricManager",
            "notify",
            "ContinuousProfiler",
            "load_config_override",
            "load_config",
            "IHubConfProvider",
            "provideUtility",
            "register_legacy_worklist_metrics",
            "initServiceManager",
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                "{src}.{target}".format(target=target, **PATH),
                autospec=True,
            )
            t.patchers[target] = patched
            setattr(t, target, patched.start())
            t.addCleanup(patched.stop)

        from_file_patcher = patch(
            "{src}.ServerConfig.from_file".format(**PATH)
        )
        t.from_file_mock = from_file_patcher.start()
        t.addCleanup(from_file_patcher.stop)
        t.from_file_mock.return_value = ServerConfig({})

        t.zh = ZenHub()

    @patch("{src}.start_server".format(**PATH), autospec=True)
    @patch("{src}.task.LoopingCall".format(**PATH), autospec=True)
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    def test_main(t, getUtility, LoopingCall, start_server):
        t.zh.options = sentinel.options
        t.zh.options.monitor = "localhost"
        t.zh.options.cycle = True
        t.zh.options.profiling = True
        t.zh.options.invalidation_poll_interval = sentinel.inval_poll
        # Metric Management
        t.zh._metric_manager = t.MetricManager.return_value
        t.zh._metric_writer = sentinel.metric_writer
        t.zh.profiler = Mock(name="profiler", spec_set=["stop"])

        t.zh.run()

        # convert to a looping call
        t.reactor.callLater.assert_called_with(0, t.zh.heartbeat)

        start_server.assert_called_once_with(
            t.reactor,
            t.make_server_factory.return_value,
        )

        LoopingCall.assert_has_calls(
            [
                call(t.zh._invalidation_manager.process_invalidations),
                call().start(sentinel.inval_poll),
                call(
                    report_reactor_delayed_calls,
                    t.zh.options.monitor,
                    t.zh.name,
                ),
                call().start(30),
            ]
        )
        t.assertEqual(
            LoopingCall.return_value,
            t.zh.process_invalidations_task,
        )

        t.assertEqual(t.zh.metricreporter, t.zh._metric_manager.metricreporter)
        t.zh._metric_manager.start.assert_called_with()
        # trigger to shut down metric reporter before zenhub exits
        t.reactor.addSystemEventTrigger.assert_has_calls(
            [
                call("before", "shutdown", t.zh._metric_manager.stop),
                call("before", "shutdown", stop_server),
            ]
        )
        # After the reactor stops:
        t.zh.profiler.stop.assert_called_with()
        # Closes IEventPublisher, which breaks old integration tests
        getUtility.assert_called_with(IEventPublisher)
        getUtility.return_value.close.assert_called_with()

    @patch("{src}.ReportWorkerStatus".format(**PATH), autospec=True)
    @patch("{src}.notify".format(**PATH), autospec=True)
    def test_sighandler_USR2(t, _notify, _ReportWorkerStatus):
        ZenHub.sighandler_USR2(t.zh, signum="unused", frame="unused")

        t.zh._status_reporter.getReport.assert_called_once_with()
        t.zh.log.info.assert_called_once_with(
            "\n%s\n",
            t.zh._status_reporter.getReport.return_value,
        )
        _notify.assert_called_once_with(_ReportWorkerStatus.return_value)
        _ReportWorkerStatus.assert_called_once_with()

    @patch("{src}.super".format(**PATH))
    @patch("{src}.signal".format(**PATH), autospec=True)
    def test_sighandler_USR1(t, signal, _super):
        t.zh.profiler = Mock(name="profiler", spec_set=["dump_stats"])
        t.zh.options = Mock(name="options", profiling=True)
        signum = sentinel.signum
        frame = sentinel.frame

        ZenHub.sighandler_USR1(t.zh, signum=signum, frame=frame)

        t.zh.profiler.dump_stats.assert_called_with()
        _super.assert_called_with(ZenHub, t.zh)
        _super.return_value.sighandler_USR1.assert_called_with(signum, frame)

    def test_stop(t):
        t.assertFalse(t.zh.shutdown)
        t.zh.stop()
        t.assertTrue(t.zh.shutdown)

    def test__getConf(t):
        ret = t.zh._getConf()
        confProvider = t.IHubConfProvider.return_value
        t.assertEqual(ret, confProvider.getHubConf.return_value)

    def test_getService(t):
        service = "service"
        monitor = "localhost"
        expected = t.zh._service_manager.getService.return_value

        result = t.zh.getService(service, monitor)

        t.assertEqual(expected, result)
        t.zh._service_manager.getService.assert_called_once_with(
            service,
            monitor,
        )

    def test_getRRDStats(t):
        t.zh._metric_manager = t.MetricManager.return_value
        t.zh._getConf = create_autospec(t.zh._getConf)

        ret = t.zh.getRRDStats()

        t.zh._metric_manager.get_rrd_stats.assert_called_with(
            t.zh._getConf(),
            t.zh.zem.sendEvent,
        )
        t.assertEqual(ret, t.zh._metric_manager.get_rrd_stats.return_value)

    @patch("{src}.Event".format(**PATH), autospec=True)
    def test_sendEvent(t, Event):
        event = {"device": "x", "component": "y", "summary": "msg"}

        t.zh.sendEvent(**event)

        Event.assert_called_with(**event)
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    @patch("{src}.Event".format(**PATH), autospec=True)
    def test_sendEvent_defaults(t, Event):
        t.zh.options = Mock(name="options", spec_set=["monitor"])

        t.zh.sendEvent(eventClass="class", summary="something", severity=0)

        Event.assert_called_with(
            device=t.zh.options.monitor,
            component=t.zh.name,
            eventClass="class",
            summary="something",
            severity=0,
        )
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    @patch("{src}.IHubHeartBeatCheck".format(**PATH), autospec=True)
    @patch("{src}.EventHeartbeat".format(**PATH), autospec=True)
    def test_heartbeat(t, EventHeartbeat, IHubHeartBeatCheck):
        t.zh.options = Mock(
            name="options",
            spec_set=["monitor", "name", "heartbeatTimeout"],
        )
        t.zh._invalidation_manager.totalTime = 100
        t.zh._invalidation_manager.totalEvents = 20
        # static value defined in function
        seconds = 30
        # Metrics reporting portion needs to be factored out
        service0 = Mock(name="service0", spec_set=["callTime"], callTime=9)
        t.zh._service_manager.getService.return_value = service0

        t.zh.heartbeat()

        EventHeartbeat.assert_called_with(
            t.zh.options.monitor,
            t.zh.name,
            t.zh.options.heartbeatTimeout,
        )
        t.zh.zem.sendEvent.assert_called_with(EventHeartbeat.return_value)
        t.zh.niceDoggie.assert_called_with(seconds)
        t.reactor.callLater.assert_called_with(seconds, t.zh.heartbeat)
        IHubHeartBeatCheck.assert_called_with(t.zh)
        IHubHeartBeatCheck.return_value.check.assert_called_with()
        # Metrics reporting, copies zenhub.counters into rrdStats.counter
        t.zh.rrdStats.counter.has_calls(
            [
                call("totalTime", int(t.zh.totalTime * 1000)),
                call("totalEvents", t.zh.totalEvents),
            ]
        )
        t.zh._monitor.update_rrd_stats.assert_called_once_with(
            t.zh.rrdStats,
            t.zh._service_manager,
        )

    @patch("{src}.ParserReadyForOptionsEvent".format(**PATH), autospec=True)
    @patch("{src}.notify".format(**PATH), autospec=True)
    @patch("{src}.zenPath".format(**PATH))
    @patch("{src}.ZCmdBase".format(**PATH))
    def test_buildOptions(
        t,
        ZCmdBase,
        zenPath,
        notify,
        ParserReadyForOptionsEvent,
    ):
        # this should call buildOptions on parent classes, up the tree
        # currently calls an ancestor class directly
        # parser expected to be added by CmdBase.buildParser
        from optparse import OptionParser

        t.zh.parser = OptionParser()
        # Given no commandline options
        sys.argv = []

        t.zh.buildOptions()
        t.zh.options, args = t.zh.parser.parse_args()

        ZCmdBase.buildOptions.assert_called_with(t.zh)
        t.assertEqual(t.zh.options.xmlrpcport, XML_RPC_PORT)
        t.assertEqual(t.zh.options.pbport, PB_PORT)
        zenPath.assert_called_with("etc", "hubpasswd")
        t.assertEqual(t.zh.options.passwordfile, zenPath.return_value)
        t.assertEqual(t.zh.options.monitor, "localhost")
        t.assertEqual(t.zh.options.workersReservedForEvents, 1)
        t.assertEqual(t.zh.options.invalidation_poll_interval, 30)
        t.assertFalse(t.zh.options.profiling)
        t.assertEqual(t.zh.options.modeling_pause_timeout, 3600)
        # delay before actually parsing the options
        notify.assert_called_with(ParserReadyForOptionsEvent(t.zh.parser))

    @patch("{src}.server_config.ModuleObjectConfig".format(**PATH))
    @patch("{src}.provideUtility".format(**PATH))
    def test_initServiceManager(t, provideUtility, ModuleObjectConfig):
        initServiceManager(t.zh.options)

        t.assertEqual(
            server_config.modeling_pause_timeout,
            int(t.zh.options.modeling_pause_timeout),
        )
        t.assertEqual(server_config.xmlrpcport, int(t.zh.options.xmlrpcport))
        t.assertEqual(server_config.pbport, int(t.zh.options.pbport))

        ModuleObjectConfig.assert_called_with(server_config)
        provideUtility.assert_called_with(
            ModuleObjectConfig.return_value, IHubServerConfig
        )


class DefaultConfProviderTest(TestCase):
    """Test the DefaultConfProvider class."""

    def test_implements_IHubConfProvider(t):
        # the class Implements the Interface
        t.assertTrue(IHubConfProvider.implementedBy(DefaultConfProvider))

    def test_adapts_ZenHub(t):
        t.assertEqual(
            adaptedBy(DefaultConfProvider),
            (ZenHub,),
        )
        t.assertIn(ZenHub, adaptedBy(DefaultConfProvider))

    def test___init__(t):
        zenhub = sentinel.zenhub

        default_conf_provider = DefaultConfProvider(zenhub)

        # the object provides the interface
        t.assertTrue(IHubConfProvider.providedBy(default_conf_provider))
        # Verify the object implments the interface properly
        verifyObject(IHubConfProvider, default_conf_provider)
        t.assertEqual(default_conf_provider._zenhub, zenhub)

    def test_getHubConf(t):
        zenhub = Mock(name="zenhub", spec_set=["dmd", "options"])
        default_conf_provider = DefaultConfProvider(zenhub)

        ret = default_conf_provider.getHubConf()

        zenhub.dmd.Monitors.Performance._getOb.assert_called_with(
            zenhub.options.monitor,
            None,
        )
        t.assertEqual(ret, zenhub.dmd.Monitors.Performance._getOb.return_value)


class DefaultHubHeartBeatCheckTest(TestCase):
    """Test the DefaultHubHeartBeatCheck class."""

    def test_implements_IHubHeartBeatCheck(t):
        # the class Implements the Interface
        t.assertTrue(
            IHubHeartBeatCheck.implementedBy(DefaultHubHeartBeatCheck),
        )

    def test_adapts_ZenHub(t):
        t.assertIn(ZenHub, adaptedBy(DefaultHubHeartBeatCheck))

    def test___init__(t):
        zenhub = sentinel.zenhub

        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)

        # the object provides the interface
        t.assertTrue(
            IHubHeartBeatCheck.providedBy(default_hub_heartbeat_check),
        )
        # Verify the object implments the interface properly
        verifyObject(IHubHeartBeatCheck, default_hub_heartbeat_check)
        t.assertEqual(default_hub_heartbeat_check._zenhub, zenhub)

    def test_check(t):
        # does nothing
        zenhub = sentinel.zenhub
        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)
        default_hub_heartbeat_check.check()


class HubWillBeCreatedEventTest(TestCase):
    """Test the HubWillBeCreatedEvent class."""

    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubWillBeCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubWillBeCreatedEvent.implementedBy(HubWillBeCreatedEvent),
        )
        # the object provides the interface
        t.assertTrue(IHubWillBeCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubWillBeCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class HubCreatedEventTest(TestCase):
    """Test the HubCreatedEvent class."""

    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(IHubCreatedEvent.implementedBy(HubCreatedEvent))
        # the object provides the interface
        t.assertTrue(IHubCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class ParserReadyForOptionsEventTest(TestCase):
    """Test the ParserReadyForOptionsEvent class."""

    def test__init__(t):
        parser = sentinel.parser
        event = ParserReadyForOptionsEvent(parser)
        # the class Implements the Interface
        t.assertTrue(
            IParserReadyForOptionsEvent.implementedBy(
                ParserReadyForOptionsEvent,
            ),
        )
        # the object provides the interface
        t.assertTrue(IParserReadyForOptionsEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IParserReadyForOptionsEvent, event)

        t.assertEqual(event.parser, parser)


class ReactorDelayedCallsMetricTest(TestCase):
    def setUp(t):
        _patchables = (("getUtility", Mock(spec=[])),)
        for name, value in _patchables:
            patcher = patch(
                "{src}.{name}".format(src=PATH["src"], name=name),
                new=value,
            )
            setattr(t, name, patcher.start())
            t.addCleanup(patcher.stop)

    @patch("{src}.time".format(**PATH))
    def test_report_reactor_delayed_calls(t, time):
        time.return_value = 555
        writer = t.getUtility.return_value.metric_writer
        hub = Mock(name="ZenHub")

        report_reactor_delayed_calls(hub.options.monitor, hub.name)

        t.getUtility.assert_called_once_with(IMetricManager)
        writer.write_metric.assert_called_once_with(
            "zenhub.reactor.delayedcalls",
            len(reactor.getDelayedCalls()),
            time.return_value * 1000,
            {"monitor": hub.options.monitor, "name": hub.name},
        )
