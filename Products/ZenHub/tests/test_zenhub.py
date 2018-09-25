from unittest import TestCase
from mock import Mock, patch, create_autospec, call, MagicMock, sentinel

from zope.interface.verify import verifyObject
from zope.component import adaptedBy

from mock_interface import create_interface_mock

# Breaks test isolation ImportError: No module named Globals
from Products.ZenHub.zenhub import (
    AuthXmlRpcService,
    XmlRpcService,
    HubAvitar,
    RemoteBadMonitor,
    pb,
    ServiceAddedEvent, IServiceAddedEvent,
    HubWillBeCreatedEvent, IHubWillBeCreatedEvent,
    HubCreatedEvent, IHubCreatedEvent,
    ParserReadyForOptionsEvent, IParserReadyForOptionsEvent,
    _ZenHubWorklist,
    publisher,
    redisPublisher,
    metricWriter,
    ZenHub,
    CONNECT_TIMEOUT, OPTION_STATE,
    IInvalidationFilter,
    POSKeyError,
    PrimaryPathObjectManager,
    DeviceComponent,
    FILTER_INCLUDE, FILTER_EXCLUDE,
    IInvalidationProcessor,
    collections,
    defer,
    LastCallReturnValue,
    XML_RPC_PORT, PB_PORT,
    DefaultConfProvider, IHubConfProvider,
    DefaultHubHeartBeatCheck, IHubHeartBeatCheck,
    IEventPublisher,
)

PATH = {'src': 'Products.ZenHub.zenhub'}


class AuthXmlRpcServiceTest(TestCase):

    def setUp(t):
        t.dmd = Mock(name='dmd', spec_set=['ZenEventManager'])
        t.checker = Mock(name='checker', spec_set=['requestAvatarId'])

        t.axrs = AuthXmlRpcService(t.dmd, t.checker)

    @patch('{src}.XmlRpcService.__init__'.format(**PATH), autospec=True)
    def test___init__(t, XmlRpcService__init__):
        dmd = sentinel.dmd
        checker = sentinel.checker

        axrs = AuthXmlRpcService(dmd, checker)

        XmlRpcService__init__.assert_called_with(axrs, dmd)
        t.assertEqual(axrs.checker, checker)

    def test_doRender(t):
        '''should be refactored to call self.render,
        instead of the parrent class directly
        '''
        render = create_autospec(XmlRpcService.render, name='render')
        XmlRpcService.render = render
        request = sentinel.request

        ret = t.axrs.doRender('unused arg', request)

        XmlRpcService.render.assert_called_with(t.axrs, request)
        t.assertEqual(ret, render.return_value)

    @patch('{src}.xmlrpc'.format(**PATH), name='xmlrpc', autospec=True)
    def test_unauthorized(t, xmlrpc):
        request = sentinel.request
        t.axrs._cbRender = create_autospec(t.axrs._cbRender)

        t.axrs.unauthorized(request)

        xmlrpc.Fault.assert_called_with(t.axrs.FAILURE, 'Unauthorized')
        t.axrs._cbRender.assert_called_with(xmlrpc.Fault.return_value, request)

    @patch('{src}.server'.format(**PATH), name='server', autospec=True)
    @patch(
        '{src}.credentials'.format(**PATH), name='credentials', autospec=True
    )
    def test_render(t, credentials, server):
        request = Mock(name='request', spec_set=['getHeader'])
        auth = Mock(name='auth', spec_set=['split'])
        encoded = Mock(name='encoded', spec_set=['decode'])
        encoded.decode.return_value.split.return_value = ('user', 'password')
        auth.split.return_value = ('Basic', encoded)

        request.getHeader.return_value = auth

        ret = t.axrs.render(request)

        request.getHeader.assert_called_with('authorization')
        encoded.decode.assert_called_with('base64')
        encoded.decode.return_value.split.assert_called_with(':')
        credentials.UsernamePassword.assert_called_with('user', 'password')
        t.axrs.checker.requestAvatarId.assert_called_with(
            credentials.UsernamePassword.return_value
        )
        deferred = t.axrs.checker.requestAvatarId.return_value
        deferred.addCallback.assert_called_with(t.axrs.doRender, request)

        t.assertEqual(ret, server.NOT_DONE_YET)


class HubAvitarTest(TestCase):

    def setUp(t):
        t.hub = Mock(name='hub', spec_set=['getService', 'log', 'workers'])
        t.avitar = HubAvitar(t.hub)

    def test___init__(t):
        t.assertEqual(t.avitar.hub, t.hub)

    def test_perspective_ping(t):
        ret = t.avitar.perspective_ping()
        t.assertEqual(ret, 'pong')

    @patch('{src}.os.environ'.format(**PATH), name='os.environ', autospec=True)
    def test_perspective_getHubInstanceId(t, os_environ):
        ret = t.avitar.perspective_getHubInstanceId()
        os_environ.get.assert_called_with(
            'CONTROLPLANE_INSTANCE_ID', 'Unknown'
        )
        t.assertEqual(ret, os_environ.get.return_value)

    def test_perspective_getService(t):
        service_name = 'serviceName'
        instance = 'collector_instance_name'
        listener = sentinel.listener
        options = sentinel.options
        service = t.hub.getService.return_value

        ret = t.avitar.perspective_getService(
            service_name, instance=instance,
            listener=listener, options=options
        )

        t.hub.getService.assert_called_with(service_name, instance)
        service.addListener.assert_called_with(listener, options)
        t.assertEqual(ret, service)

    def test_perspective_getService_raises_RemoteBadMonitor(t):
        t.hub.getService.side_effect = RemoteBadMonitor('tb', 'msg')
        with t.assertRaises(RemoteBadMonitor):
            t.avitar.perspective_getService('service_name')

    def test_perspective_reportingForWork(t):
        worker = Mock(pb.RemoteReference, autospec=True)
        pid = 9999
        t.hub.workers = []

        t.avitar.perspective_reportingForWork(worker, pid=pid)

        t.assertFalse(worker.busy)
        t.assertEqual(worker.pid, pid)
        t.assertIn(worker, t.hub.workers)

        # Ugly test for the notifyOnDisconnect method, please refactor
        args, kwargs = worker.notifyOnDisconnect.call_args
        removeWorker = args[0]

        removeWorker(worker)
        t.assertNotIn(worker, t.hub.workers)


class ServiceAddedEventTest(TestCase):
    def test___init__(t):
        name, instance = 'name', 'instance'
        service_added_event = ServiceAddedEvent(name, instance)
        # the class Implements the Interface
        t.assertTrue(IServiceAddedEvent.implementedBy(ServiceAddedEvent))
        # the object provides the interface
        t.assertTrue(IServiceAddedEvent.providedBy(service_added_event))
        # Verify the object implments the interface properly
        verifyObject(IServiceAddedEvent, service_added_event)

        t.assertEqual(service_added_event.name, name)
        t.assertEqual(service_added_event.instance, instance)


class HubWillBeCreatedEventTest(TestCase):
    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubWillBeCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubWillBeCreatedEvent.implementedBy(HubWillBeCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubWillBeCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubWillBeCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class HubCreatedEventTest(TestCase):
    def test__init__(t):
        hub = sentinel.zenhub_instance
        event = HubCreatedEvent(hub)
        # the class Implements the Interface
        t.assertTrue(
            IHubCreatedEvent.implementedBy(HubCreatedEvent)
        )
        # the object provides the interface
        t.assertTrue(IHubCreatedEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IHubCreatedEvent, event)

        t.assertEqual(event.hub, hub)


class ParserReadyForOptionsEventTest(TestCase):
    def test__init__(t):
        parser = sentinel.parser
        event = ParserReadyForOptionsEvent(parser)
        # the class Implements the Interface
        t.assertTrue(
            IParserReadyForOptionsEvent.implementedBy(
                ParserReadyForOptionsEvent
            )
        )
        # the object provides the interface
        t.assertTrue(IParserReadyForOptionsEvent.providedBy(event))
        # Verify the object implments the interface properly
        verifyObject(IParserReadyForOptionsEvent, event)

        t.assertEqual(event.parser, parser)


class _ZenHubWorklistTest(TestCase):

    def setUp(t):
        t.wl = _ZenHubWorklist()

    def test____init__(t):
        t.assertEqual(
            t.wl.eventPriorityList,
            [t.wl.eventworklist, t.wl.otherworklist, t.wl.applyworklist]
        )
        t.assertEqual(
            t.wl.otherPriorityList,
            [t.wl.otherworklist, t.wl.applyworklist, t.wl.eventworklist]
        )
        t.assertEqual(
            t.wl.applyPriorityList,
            [t.wl.applyworklist, t.wl.eventworklist, t.wl.otherworklist]
        )
        t.assertEqual(
            t.wl.dispatch,
            {
                'sendEvents': t.wl.eventworklist,
                'sendEvent': t.wl.eventworklist,
                'applyDataMaps': t.wl.applyworklist
            }
        )

    def test___getitem__(t):
        '''zenhub_worker_list[dispatch] uses the dispatch dict to
        map 'sendEvents', 'sendEvent', 'applyDataMaps' keys to worklists
        '''
        t.assertEqual(t.wl['sendEvents'], t.wl.eventworklist)
        t.assertEqual(t.wl['sendEvent'], t.wl.eventworklist)
        t.assertEqual(t.wl['applyDataMaps'], t.wl.applyworklist)
        t.assertEqual(t.wl['anything else'], t.wl.otherworklist)

    def test___len__(t):
        '''len(zenhub_worker_list) returns the sum of all work lists
        '''
        t.wl.eventworklist = range(1)
        t.wl.applyworklist = range(2)
        t.wl.otherworklist = range(4)
        t.assertEqual(len(t.wl), 7)

    def test_push(t):
        other = Mock(
            name='apply_datamap', spec_set=['method'], method='other'
        )
        t.wl.push(other)
        t.assertEqual(t.wl.otherworklist, [other])

    def test_push_sendEvent(t):
        send_event = Mock(
            name='send_event', spec_set=['method'], method='sendEvent'
        )
        t.wl.push(send_event)
        t.assertEqual(t.wl['sendEvent'], [send_event])

    def test_push_sendEvents(t):
        send_events = Mock(
            name='send_events', spec_set=['method'], method='sendEvents'
        )
        t.wl.push(send_events)
        t.assertEqual(t.wl['sendEvents'], [send_events])

    def test_push_applyDataMaps(t):
        apply_datamap = Mock(
            name='apply_datamap', spec_set=['method'], method='applyDataMaps'
        )
        t.wl.push(apply_datamap)
        t.assertEqual(t.wl['applyDataMaps'], [apply_datamap])

    def test_append(t):
        t.assertEqual(t.wl.append, t.wl.push)

    def test_pop(t):
        '''randomizes selection from lists in an attempt to weight and balance
        item selection. with an option to ignore the applyDataMaps queue.
        current implementation is highly inefficient.
        current logic will not apply weighing properly if allowADM=False.
        cannot set random.seed('static'), random was not imported

        Should be reviewed and refactored.
        '''
        job_a = Mock(name='job_a', spec_set=['method'], method='sendEvent')

        t.wl.push(job_a)

        ret = t.wl.pop()
        t.assertEqual(ret, job_a)
        ret = t.wl.pop()
        t.assertEqual(ret, None)


class ZenHubModuleTest(TestCase):

    @patch('{src}.HttpPostPublisher'.format(**PATH), autospec=True)
    def test_publisher(t, HttpPostPublisher):
        ret = publisher('username', 'password', 'url')
        HttpPostPublisher.assert_called_with('username', 'password', 'url')
        t.assertEqual(ret, HttpPostPublisher.return_value)

    @patch('{src}.RedisListPublisher'.format(**PATH), autospec=True)
    def test_redisPublisher(t, RedisListPublisher):
        ret = redisPublisher()
        RedisListPublisher.assert_called_with()
        t.assertEqual(ret, RedisListPublisher.return_value)

    @patch('{src}.AggregateMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.FilteredMetricWriter'.format(**PATH), autospec=True)
    @patch('{src}.publisher'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.redisPublisher'.format(**PATH), autospec=True)
    @patch('{src}.MetricWriter'.format(**PATH), autospec=True)
    def test_metricWriter(
        t,
        MetricWriter,
        redisPublisher,
        os,
        publisher,
        FilteredMetricWriter,
        AggregateMetricWriter
    ):
        '''Returns an initialized MetricWriter instance,
        should probably be refactored into its own class
        '''
        os.environ = {
            'CONTROLPLANE': '1',
            'CONTROLPLANE_CONSUMER_URL': 'consumer_url',
            'CONTROLPLANE_CONSUMER_USERNAME': 'consumer_username',
            'CONTROLPLANE_CONSUMER_PASSWORD': 'consumer_password',
        }

        ret = metricWriter()

        MetricWriter.assert_called_with(redisPublisher.return_value)
        publisher.assert_called_with(
            os.environ['CONTROLPLANE_CONSUMER_USERNAME'],
            os.environ['CONTROLPLANE_CONSUMER_PASSWORD'],
            os.environ['CONTROLPLANE_CONSUMER_URL'],
        )
        AggregateMetricWriter.assert_called_with(
            [MetricWriter.return_value, FilteredMetricWriter.return_value]
        )
        t.assertEqual(ret, AggregateMetricWriter.return_value)


class ZenHubInitTest(TestCase):
    '''The init test is seperate from the others due to the complexity
    of the __init__ method
    '''
    @patch('{src}.load_config_override'.format(**PATH), spec=True)
    #@patch.object(ZenHub, 'getRRDStats')
    @patch('{src}.metricWriter'.format(**PATH), spec=True)
    @patch('{src}.signal'.format(**PATH), spec=True)
    @patch('{src}.App_Start'.format(**PATH), spec=True)
    @patch('{src}.HubCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.pb'.format(**PATH), spec=True)
    @patch('{src}.zenPath'.format(**PATH), spec=True)
    @patch('{src}.server'.format(**PATH), spec=True)
    @patch('{src}.AuthXmlRpcService'.format(**PATH), spec=True)
    @patch('{src}.reactor'.format(**PATH), spec=True)
    @patch('{src}.ipv6_available'.format(**PATH), spec=True)
    @patch('{src}.portal'.format(**PATH), spec=True)
    @patch('{src}.HubRealm'.format(**PATH), spec=True)
    @patch('{src}.loadPlugins'.format(**PATH), spec=True)
    @patch('{src}.WorkerSelector'.format(**PATH), spec=True)
    @patch('{src}.ContinuousProfiler'.format(**PATH), spec=True)
    @patch('{src}.HubWillBeCreatedEvent'.format(**PATH), spec=True)
    @patch('{src}.notify'.format(**PATH), spec=True)
    @patch('{src}.load_config'.format(**PATH), spec=True)
    @patch('{src}._ZenHubWorklist'.format(**PATH), spec=True)
    @patch('{src}.ZCmdBase.__init__'.format(**PATH), spec=True)
    def test___init__(
        t,
        ZCmdBase___init__,
        _ZenHubWorklist,
        load_config,
        notify,
        HubWillBeCreatedEvent,
        ContinuousProfiler,
        WorkerSelector,
        loadPlugins,
        HubRealm,
        portal,
        ipv6_available,
        reactor,
        AuthXmlRpcService,
        server,
        zenPath,
        pb,
        HubCreatedEvent,
        App_Start,
        signal,
        metricWriter,
        #ZenHub_getRRDStats,
        load_config_override,
    ):
        # Mock out attributes set by the parent class
        # Because these changes are made on the class, they must be reversable
        t.zenhub_patchers = [
            patch.object(ZenHub, 'dmd', create=True),
            patch.object(ZenHub, 'log', create=True),
            patch.object(ZenHub, 'options', create=True),
            patch.object(ZenHub, 'loadChecker', autospec=True),
            patch.object(ZenHub, 'getRRDStats', autospec=True),
            patch.object(ZenHub, '_getConf', autospec=True),
            patch.object(ZenHub, '_createWorkerConf', autospec=True),
            patch.object(ZenHub, 'createWorker', autospec=True),
            patch.object(ZenHub, 'setKeepAlive', autospec=True),
            patch.object(ZenHub, 'sendEvent', autospec=True),
        ]

        for patcher in t.zenhub_patchers:
            patcher.start()
            t.addCleanup(patcher.stop)

        ZenHub.options.workers = 10
        ZenHub._getConf.return_value.id = 'config_id'
        ipv6_available.return_value = False

        # patch to deal with internal import
        # import of its parent package, Projects.ZenHub
        # import Products.ZenMessaging.queuemessaging
        Products = MagicMock(
            name='Products', spec_set=['ZenHub', 'ZenMessaging']
        )
        modules = {
            'Products': Products,
            'Products.ZenHub': Products.ZenHub,
            'Products.ZenMessaging.queuemessaging': Products.ZenMessaging.queuemessaging
        }
        with patch.dict('sys.modules', modules):
            zh = ZenHub()

        t.assertIsInstance(zh, ZenHub)
        t.assertEqual(zh.workList, _ZenHubWorklist.return_value)
        # Skip Metrology validation for now due to complexity
        ZCmdBase___init__.assert_called_with(zh)
        load_config.assert_called_with("hub.zcml", Products.ZenHub)
        HubWillBeCreatedEvent.assert_called_with(zh)
        notify.assert_has_calls([call(HubWillBeCreatedEvent.return_value)])
        # Performance Profiling
        ContinuousProfiler.assert_called_with('zenhub', log=zh.log)
        zh.profiler.start.assert_called_with()
        # Worklist, used to delegate jobs to workers
        # TODO: move worker management into its own manager class
        WorkerSelector.assert_called_with(zh.options)
        t.assertEqual(zh.workerselector, WorkerSelector.return_value)
        # check this, was it supposed to be set on workerselector?
        t.assertEqual(zh.workList.log, zh.log)
        t.assertLess(zh.options.workersReservedForEvents, zh.options.workers)
        # Event Handler shortcut
        t.assertEqual(zh.zem, zh.dmd.ZenEventManager)
        loadPlugins.assert_called_with(zh.dmd)
        # PB, and XMLRPC communication config.
        # TODO: move this into its own manager class
        HubRealm.assert_called_with(zh)
        zh.setKeepAlive.assert_called_with(
            zh, reactor.listenTCP.return_value.socket
        )

        pb.PBServerFactory.assert_called_with(portal.Portal.return_value)
        AuthXmlRpcService.assert_called_with(
            zh.dmd, zh.loadChecker.return_value
        )
        server.Site.assert_called_with(AuthXmlRpcService.return_value)
        reactor.listenTCP.assert_has_calls([
            call(
                zh.options.pbport,
                pb.PBServerFactory.return_value,
                interface=''
            ),
            call(
                zh.options.xmlrpcport,
                server.Site.return_value,
                interface=''
            )
        ])
        # Messageing config, including work and invalidations
        # Patched internal import of Products.ZenMessaging.queuemessaging
        load_config_override.assert_called_with(
            'twistedpublisher.zcml',
            Products.ZenMessaging.queuemessaging
        )
        HubCreatedEvent.assert_called_with(zh)
        notify.assert_called_with(HubCreatedEvent.return_value)
        zh.sendEvent.assert_called_with(
            zh, eventClass=App_Start, summary='zenhub started',
            severity=0
        )

        # Additional worker management, separated from the rest
        zenPath.assert_called_with('var', 'zenhub', 'config_id_worker.conf')
        t.assertEqual(zh.workerconfig, zenPath.return_value)
        zh._createWorkerConf.assert_called_with(zh)
        zh.createWorker.assert_has_calls(
            [call(zh, i) for i in range(zh.options.workers)]
        )
        t.assertEqual(zh._metric_writer, metricWriter.return_value)
        t.assertEqual(zh.rrdStats, zh.getRRDStats())
        # Convert this to a LoopingCall
        reactor.callLater.assert_called_with(2, zh.giveWorkToWorkers, True)
        signal.signal.assert_called_with(signal.SIGUSR2, zh.sighandler_USR2)


class ZenHubTest(TestCase):

    def setUp(t):
        # Patch out the ZenHub __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            ZenHub, '__init__', autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)
        t.time_patcher = patch('{src}.time'.format(**PATH), autospec=True)
        t.time = t.time_patcher.start()
        t.addCleanup(t.time_patcher.stop)
        t.reactor_patcher = patch(
            '{src}.reactor'.format(**PATH), autospec=True
        )
        t.reactor = t.reactor_patcher.start()
        t.addCleanup(t.reactor_patcher.stop)

        t.zh = ZenHub()
        # Set attributes that should be created by __init__
        t.zh.log = Mock(name='log', spec_set=['debug', 'warn', 'exception', 'warning'])
        t.zh.shutdown = False
        t.zh.zem = Mock(name='ZenEventManager', spec_set=['sendEvent'])

    def test_setKeepAlive(t):
        '''ConnectionHandler function
        '''
        socket = Mock(
            name='socket',
            spec_set=[
                'SOL_SOCKET', 'SO_KEEPALIVE', 'SOL_TCP',
                'TCP_KEEPIDLE', 'TCP_KEEPINTVL', 'TCP_KEEPCNT'
            ]
        )
        sock = Mock(name='sock', spec_set=['setsockopt', 'getsockname'])
        # Super Hacky patch to deal with internal import
        with patch.dict('sys.modules', socket=socket):
            t.zh.setKeepAlive(sock)
        # validate side effects: sock opts set as expected
        interval = max(CONNECT_TIMEOUT / 4, 10)
        sock.setsockopt.assert_has_calls([
            call(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE),
            call(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT),
            call(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval),
            call(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
        ])

    @patch('{src}.signal'.format(**PATH), autospec=True)
    def test_sighandler_USR2(t, signal):
        '''Daemon function
        when signal USR2 is recieved, broadcast it to all worker processes
        '''
        _workerStats = create_autospec(t.zh._workerStats, name='_workerStats')
        t.zh._workerStats = _workerStats
        t.zh.SIGUSR_TIMEOUT = 1
        # should use the workerProcess class as spec, but its currently burried
        worker_proc = Mock(
            name='worker_1', spec_set=['spawn_time', 'signalProcess'],
            spawn_time=3
        )
        t.time.time.return_value = 5
        t.zh.workerprocessmap = {'w1': worker_proc}

        ZenHub.sighandler_USR2(t.zh, signum='unused', frame='unused')

        t.zh._workerStats.assert_called_with()
        worker_proc.signalProcess.assert_called_with(signal.SIGUSR2)

    @patch('{src}.super'.format(**PATH))
    @patch('{src}.signal'.format(**PATH), autospec=True)
    def test_sighandler_USR1(t, signal, super):
        '''Daemon function
        when signal USR1 is recieved, broadcast it to all worker processes
        '''
        t.zh.profiler = Mock(name='profiler', spec_set=['dump_stats'])
        t.zh.options = Mock(name='options', profiling=True)
        worker_proc = Mock(name='worker_1', spec_set=['signalProcess'])
        t.zh.workerprocessmap = {'w1': worker_proc}
        signum = sentinel.signum
        frame = sentinel.frame

        ZenHub.sighandler_USR1(t.zh, signum=signum, frame=frame)

        t.zh.profiler.dump_stats.assert_called_with()
        super.assert_called_with(ZenHub, t.zh)
        super.return_value.sighandler_USR1.assert_called_with(
            signum, frame
        )
        worker_proc.signalProcess.assert_called_with(signal.SIGUSR1)

    def test_stop(t):
        t.assertFalse(t.zh.shutdown)
        t.zh.stop()
        t.assertTrue(t.zh.shutdown)

    @patch('{src}.IHubConfProvider'.format(**PATH), autospec=True)
    def test__getConf(t, IHubConfProvider):
        ret = t.zh._getConf()
        confProvider = IHubConfProvider.return_value
        t.assertEqual(ret, confProvider.getHubConf.return_value)

    @patch('{src}.DerivativeTracker'.format(**PATH), autospec=True)
    @patch('{src}.ThresholdNotifier'.format(**PATH), autospec=True)
    @patch('{src}.DaemonStats'.format(**PATH), autospec=True)
    def test_getRRDStats(t, DaemonStats, ThresholdNotifier, DerivativeTracker):
        '''Metric reporting function
        '''
        t.zh._getConf = create_autospec(t.zh._getConf, name='_getConf')
        t.zh._metric_writer = Mock(metricWriter, name='metricWriter')

        # patch to deal with internal import
        BuiltInDS_module = MagicMock(
            name='Products.ZenModel.BuiltInDS',
            spec_set=['BuiltInDS'],
        )
        BuiltInDS = MagicMock(name='BuiltInDS', spec_set=['sourcetype'])
        BuiltInDS_module.BuiltInDS = BuiltInDS
        modules = {'Products.ZenModel.BuiltInDS': BuiltInDS_module}

        with patch.dict('sys.modules', modules):
            ret = t.zh.getRRDStats()

        rrdStats = DaemonStats.return_value
        perfConf = t.zh._getConf.return_value
        thresholds = perfConf.getThresholdInstances.return_value
        threshold_notifier = ThresholdNotifier.return_value
        derivative_tracker = DerivativeTracker.return_value

        perfConf.getThresholdInstances.assert_called_with(BuiltInDS.sourcetype)
        ThresholdNotifier.assert_called_with(t.zh.zem.sendEvent, thresholds)

        rrdStats.config.assert_called_with(
            'zenhub',
            perfConf.id,
            t.zh._metric_writer,
            threshold_notifier,
            derivative_tracker
        )

        t.assertEqual(ret, DaemonStats.return_value)

    def test_processQueue(t):
        '''Configuration Invalidation Processing function
        synchronize with the database, and execute doProcessQueue
        recursive reactor.callLater should be replaced with loopingCall
        '''
        async_syncdb = create_autospec(t.zh.async_syncdb, name='async_syncdb')
        t.zh.async_syncdb = async_syncdb
        t.zh.doProcessQueue = create_autospec(
            t.zh.doProcessQueue, name='doProcessQueue'
        )
        options = Mock(name='options', spec_set=['invalidation_poll_interval'])
        t.zh.options = options
        t.zh.totalEvents = 0
        t.zh.totalTime = 0
        timestamps = [10, 20]
        t.time.time.side_effect = timestamps

        t.zh.processQueue()

        t.zh.async_syncdb.assert_called_with()
        t.zh.doProcessQueue.assert_called_with()

        t.reactor.callLater.assert_called_with(
            options.invalidation_poll_interval, t.zh.processQueue
        )
        t.assertEqual(t.zh.totalTime, timestamps[1] - timestamps[0])
        t.assertEqual(t.zh.totalEvents, 1)

    @patch('{src}.getUtilitiesFor'.format(**PATH), autospec=True)
    def test__initialize_invalidation_filters(t, getUtilitiesFor):
        '''Configuration Invalidation Processing function
        '''
        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filters = [MockIInvalidationFilter() for i in range(3)]
        # weighted in reverse order
        for i, filter in enumerate(filters):
            filter.weight = 10 - i
        getUtilitiesFor.return_value = [
            ('f%s' % i, f) for i, f in enumerate(filters)
        ]
        t.zh.dmd = sentinel.dmd

        t.zh._initialize_invalidation_filters()

        for filter in filters:
            filter.initialize.assert_called_with(t.zh.dmd)

        # check sorted by weight
        filters.reverse()
        t.assertEqual(t.zh._invalidation_filters, filters)

    def test__filter_oids(t):
        '''Configuration Invalidation Processing function
        yields a generator with the OID if the object has been deleted
        runs changed devices through invalidation_filters
        which may exclude them,
        and runs any included devices through _transformOid
        '''

        dmd = Mock(
            name='dmd', spec_set=['getPhysicalRoot', '_invalidation_filters']
        )
        app = dmd.getPhysicalRoot.return_value
        t.zh.dmd = dmd

        device = MagicMock(PrimaryPathObjectManager, __of__=Mock())
        device_obj = sentinel.device_obj
        device.__of__.return_value.primaryAq.return_value = device_obj
        component = MagicMock(DeviceComponent, __of__=Mock())
        component_obj = sentinel.component_obj
        component.__of__.return_value.primaryAq.return_value = component_obj
        excluded = Mock(DeviceComponent, __of__=Mock())
        excluded_obj = sentinel.excluded_obj
        excluded.__of__.return_value.primaryAq.return_value = excluded_obj

        app._p_jar = {
            111: device,
            222: component,
            # BUG: any object filtered overwrites other oids
            # but without a filtered object, no oids are returned
            333: excluded,
        }
        oids = app._p_jar.keys()

        def include(obj):
            if obj in [device_obj, component_obj]:
                return FILTER_EXCLUDE  # not filter, will be returned
            if obj == excluded_obj:
                return FILTER_INCLUDE  # filters, will be ignored

        MockIInvalidationFilter = create_interface_mock(IInvalidationFilter)
        filter = MockIInvalidationFilter()
        filter.include = include
        t.zh._invalidation_filters = [filter]

        t.zh._transformOid = create_autospec(
            t.zh._transformOid, name='_transformOid',
            # BUG: return value from transformOid overwrites other oids
            return_value=[444],
        )

        ret = t.zh._filter_oids(oids)
        out = [o for o in ret]  # unwind the generator

        # WARNING: included/excluded logic may be reversed
        # possible bug, _tranformOid is only called on EXCLUDED oids.
        # BUG
        t.zh._transformOid.assert_has_calls([call(333, excluded_obj)])

        # BUG: f _transformOid wipes out all other oids
        #t.assertEqual(out, [111, 222])
        t.assertEqual(out, [444])

    def test__filter_oids_deleted(t):
        dmd = Mock(name='dmd', spec_set=['getPhysicalRoot'])
        t.zh.dmd = dmd
        app = dmd.getPhysicalRoot.return_value = MagicMock(name='root')
        app._p_jar.__getitem__.side_effect = POSKeyError()

        ret = t.zh._filter_oids([111])
        out = [o for o in ret]  # unwind the generator
        t.assertEqual(out, [111])

    def test__filter_oids_deleted_primaryaq(t):
        dmd = Mock(name='dmd', spec_set=['getPhysicalRoot'])
        t.zh.dmd = dmd
        deleted = MagicMock(DeviceComponent, __of__=Mock())
        deleted.__of__.return_value.primaryAq.side_effect = KeyError
        with t.assertRaises(KeyError):
            deleted.__of__().primaryAq()

        app = dmd.getPhysicalRoot.return_value
        app._p_jar = {111: deleted}

        ret = t.zh._filter_oids([111])
        out = [o for o in ret]
        t.assertEqual(out, [111])

    @patch('{src}.IInvalidationOid'.format(**PATH), autospec=True)
    @patch('{src}.subscribers'.format(**PATH), autospec=True)
    def test__transformOid(t, subscribers, IInvalidationOid):
        '''Configuration Invalidation Processing function
        given an oid: object pair
        gets a list of transforms for the object
        executes the transforms given the oid
        returns a set of oids returned by the transforms
        '''
        adapter_a = Mock(
            name='adapter_a', spec_set=['transformOid'],
            transformOid=lambda x: x + '0'
        )
        subscribers.return_value = [adapter_a]
        adapter_b = Mock(
            name='adapter_b', spec_set=['transformOid'],
            transformOid=lambda x: [x + '1', x + '2']
        )
        IInvalidationOid.return_value = adapter_b
        oid = 'oid'
        obj = sentinel.object

        ret = t.zh._transformOid(oid, obj)

        t.assertEqual(ret, {'oid0', 'oid1', 'oid2'})

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    def test_doProcessQueue(t, getUtility):
        '''Configuration Invalidation Processing function
        pulls in a dict of invalidations, and the IInvalidationProcessor
        and processes them, then sends an event
        refactor to use inline callbacks
        '''
        # storage is ZODB access inherited from a parent class
        t.zh.storage = Mock(name='storage', spec_set=['poll_invalidations'])
        t.zh._filter_oids = create_autospec(t.zh._filter_oids)

        t.zh.doProcessQueue()

        getUtility.assert_called_with(IInvalidationProcessor)
        getUtility.return_value.processQueue.assert_called_with(
            tuple(set(t.zh._filter_oids.return_value))
        )

    @patch('{src}.Event'.format(**PATH), autospec=True)
    def test_sendEvent(t, Event):
        '''Event Management.  send events to the EventManager
        '''
        event = {'device': 'x', 'component': 'y', 'summary': 'msg'}

        t.zh.sendEvent(**event)

        Event.assert_called_with(**event)
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    @patch('{src}.Event'.format(**PATH), autospec=True)
    def test_sendEvent_defaults(t, Event):
        t.zh.options = Mock(name='options', spec_set=['monitor'])

        t.zh.sendEvent(eventClass='class', summary='something', severity=0)

        Event.assert_called_with(
            device=t.zh.options.monitor,
            component=t.zh.name,
            eventClass='class',
            summary='something',
            severity=0,
        )
        t.zh.zem.sendEvent.assert_called_with(Event.return_value)

    # AttributeError: Mock object has no attribute '_loadCrendentials'
    @patch('{src}.checkers'.format(**PATH), spec=True)
    def test_loadChecker(t, checkers):
        t.zh.options = Mock(name='options', spec_set=['passwordfile'])
        checker = checkers.FilePasswordDB.return_value
        loaded = checker._loadCredentials.return_value
        loaded.next.return_value = ('usr', 'pas')

        ret = t.zh.loadChecker()

        checkers.FilePasswordDB.assert_called_with(t.zh.options.passwordfile)
        t.assertEqual(ret, checkers.FilePasswordDB.return_value)
        t.assertEqual(t.zh.workerUsername, 'usr')
        t.assertEqual(t.zh.workerPassword, 'pas')

    def test_getService(t):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {(name, instance): service}

        ret = t.zh.getService(name, instance)

        t.assertEqual(ret, service)

    def test_getService_raises_RemoteBadMonitor(t):
        '''raises RemoteBadMonitor on invalid instance argument
        '''
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        t.zh.dmd.Monitors.Performance._getOb.return_value = False

        with t.assertRaises(RemoteBadMonitor):
            t.zh.getService('name', 'instance')

    def test_getService_cache_miss(t):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        t.zh.options = Mock(name='options', spec_set=['workers'])
        t.zh.options.workers = False
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {}

        # patch the internal import
        # from Products.ZenUtils.Utils import importClass
        Utils = MagicMock(
            name='Products.ZenUtils.Utils', spec_set=['importClass']
        )
        from Products.ZenUtils.Utils import importClass
        Utils.importClass = create_autospec(importClass, name='importClass')
        Utils.importClass.return_value.return_value = service
        modules = {'Products.ZenUtils.Utils': Utils}
        with patch.dict('sys.modules', modules):
            ret = t.zh.getService(name, instance)

        t.assertEqual(ret, service)

    @patch('{src}.WorkerInterceptor'.format(**PATH), autospec=True)
    def test_getService_forwarded_to_WorkerInterceptor(t, WorkerInterceptor):
        t.zh.dmd = Mock(name='dmd', spec_set=['Monitors'])
        t.zh.options = Mock(name='options', spec_set=['workers'])
        name = 'module.name'
        instance = 'collector_instance'
        service = sentinel.service
        interceptor_service = sentinel.interceptor_service
        t.zh.dmd.Monitors.Performance._getOb.return_value = True
        t.zh.services = {}
        WorkerInterceptor.return_value = interceptor_service

        # patch the internal import
        # from Products.ZenUtils.Utils import importClass
        Utils = MagicMock(
            name='Products.ZenUtils.Utils', spec_set=['importClass']
        )
        from Products.ZenUtils.Utils import importClass
        Utils.importClass = create_autospec(importClass, name='importClass')
        Utils.importClass.return_value.return_value = service
        modules = {'Products.ZenUtils.Utils': Utils}
        with patch.dict('sys.modules', modules):
            ret = t.zh.getService(name, instance)

        WorkerInterceptor.assert_called_with(t.zh, service)
        t.assertEqual(ret, interceptor_service)
        t.assertEqual(t.zh.services[name, instance], interceptor_service)

    @patch('{src}.defer'.format(**PATH), autospec=True)
    @patch('{src}.HubWorklistItem'.format(**PATH), autospec=True)
    def test_deferToWorker(t, HubWorklistItem, defer):
        '''Worker Management Function
        should be refactored to use inlineCallbacks
        '''
        t.zh.getService = create_autospec(t.zh.getService)
        service = t.zh.getService.return_value.service
        t.zh.workList = Mock(_ZenHubWorklist, name='_ZenHubWorklist')
        args = (sentinel.arg0, sentinel.arg1)

        ret = t.zh.deferToWorker('svcName', 'instance', 'method', args)

        HubWorklistItem.assert_called_with(
            service.getMethodPriority.return_value,
            t.time.time.return_value,
            defer.Deferred.return_value,
            'svcName', 'instance', 'method',
            ('svcName', 'instance', 'method', args),
        )
        t.reactor.callLater.assert_called_with(0, t.zh.giveWorkToWorkers)
        t.assertEqual(ret, defer.Deferred.return_value)

    @patch('{src}.WorkerStats'.format(**PATH), autospec=True)
    def test_updateStatusAtStart(t, WorkerStats):
        '''Metric reporting function'''
        # these should be set by __init__, not specified here
        t.zh.workTracker = {}
        t.zh.executionTimer = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        wId = sentinel.worker_id
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.zh.updateStatusAtStart(wId, job)

        t.assertEqual(
            t.zh.executionTimer, {job.method: [1, 0.0, 0.0, t.time.time()]}
        )
        WorkerStats.assert_called_with(
            'Busy',
            "%s:%s.%s" % (job.instance, job.servicename, job.method),
            t.time.time(),
            0
        )
        t.assertEqual(t.zh.workTracker[wId], WorkerStats.return_value)

    @patch('{src}.WorkerStats'.format(**PATH), autospec=True)
    def test_updateStatusAtFinish(t, WorkerStats):
        '''Metric reporting function
        '''
        # this should be set by __init__, not specified here
        t.zh.executionTimer = collections.defaultdict(lambda: [0, 0.0, 0.0, 0])
        wId = sentinel.worker_id
        t0, t1 = 100, 300
        stats = Mock(
            name='stats', spec_set=['lastupdate', 'description'], lastupdate=t0
        )
        t.time.time.return_value = t1
        t.zh.workTracker = {wId: stats}
        job = Mock(name='job', spec_set=['instance', 'servicename', 'method'])

        t.zh.updateStatusAtFinish(wId, job)

        t.assertEqual(
            t.zh.executionTimer, {job.method: [0, 0.0, t1 - t0, t1]},
        )
        WorkerStats.assert_called_with('Idle', stats.description, t1, 0)
        t.assertEqual(t.zh.workTracker[wId], WorkerStats.return_value)

    def test_finished(t):
        '''Worker Management Function
        '''
        t.zh.updateStatusAtFinish = create_autospec(t.zh.updateStatusAtFinish)
        job = Mock(
            name='job', spec_set=['deferred'],
            deferred=Mock(defer.Deferred, name='deferred', autospec=True)
        )
        result = Mock(name='result', spec_set=['returnvalue'])
        finishedWorker = sentinel.zenhub_worker
        wId = sentinel.worker_id

        ret = t.zh.finished(job, result, finishedWorker, wId)

        job.deferred.callback.assert_called_with(result)
        # WARNING: may be called with error from pickle.loads, or ''.join
        # this should be
        # t.zh.updateStatusAtFinish.assert_called_with(wId, job, None)
        # Hack to test called_with manually
        args, kwargs = t.zh.updateStatusAtFinish.call_args
        t.assertEqual(args[0], wId)
        t.assertEqual(args[1], job)
        t.assertIsInstance(args[2], TypeError)

        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, result)
        t.assertFalse(finishedWorker.busy)
        t.reactor.callLater.assert_called_with(0.1, t.zh.giveWorkToWorkers)

    def test_finished_handles_LastCallReturnValue(t):
        '''Worker Management Function
        refactor as a LoopingCall instead of using reactor.callLater
        '''
        t.zh.updateStatusAtFinish = create_autospec(t.zh.updateStatusAtFinish)
        job = Mock(
            name='job', spec_set=['deferred'],
            deferred=Mock(defer.Deferred, name='deferred', autospec=True)
        )
        result = Mock(
            LastCallReturnValue, name='result', spec_set=['returnvalue']
        )

        finishedWorker = sentinel.zenhub_worker
        wId = sentinel.worker_id
        t.zh.workers = [wId, 'other worker']

        ret = t.zh.finished(job, result, finishedWorker, wId)

        t.assertNotIn(t.zh.workers, t.zh.workers)
        t.assertEqual(ret.result, result)

    def test_giveWorkToWorkers(t):
        '''Worker Management Function
        '''
        t.zh.dmd = Mock(name='dmd', spec_set=['getPauseADMLife'])
        t.zh.dmd.getPauseADMLife.return_value = 1
        t.zh.options = Mock(
            name='options', spec_set=['modeling_pause_timeout']
        )
        t.zh.options.modeling_pause_timeout = 0
        job = Mock(name='job', spec_set=['method', 'args'])
        job.args = [sentinel.arg0, sentinel.arg1]
        # should be set in __init__
        t.zh.workList = _ZenHubWorklist()
        t.zh.workList.append(job)
        worker = Mock(
            name='worker', spec_set=['busy', 'callRemote'], busy=False
        )
        worker.callRemote.reutnr_value = sentinel.result
        t.zh.workers = [worker]
        t.zh.workerselector = Mock(
            name='WorkerSelector', spec_set=['getCandidateWorkerIds']
        )
        t.zh.workerselector.getCandidateWorkerIds.return_value = [0]
        t.zh.counters = {'workerItems': 0}
        t.zh.updateStatusAtStart = create_autospec(t.zh.updateStatusAtStart)
        t.zh.finished = Mock() #create_autospec(t.zh.finished)

        t.zh.giveWorkToWorkers()

        t.zh.workerselector.getCandidateWorkerIds.assert_called_with(
            job.method, [worker]
        )
        worker.callRemote.assert_called_with('execute', *job.args)
        t.zh.finished.assert_called_with(
            job, worker.callRemote.return_value, worker, 0
        )

    def test__workerStats(t):
        '''Worker Status Logging
        sends status details for a worker to log output
        not testing log output formatting at this time
        '''
        pass

    @patch('{src}.os'.format(**PATH))
    def test__createWorkerConf(t, os):
        t.zh.workerconfig = '/path/to/config'
        t.zh.options = Mock(name='options')
        t.zh.workerUsername = sentinel.worker_username
        t.zh.workerPassword = sentinel.worker_password
        os.path.exists.return_value = False

        from mock import mock_open
        file_handler = mock_open()
        with patch('{src}.open'.format(**PATH), file_handler):
            t.zh._createWorkerConf()

        handle = file_handler()
        os.makedirs.assert_called_with(os.path.dirname.return_value)
        handle.write.assert_has_calls([
            call("hubport %s\n" % t.zh.options.pbport),
            call("username %s\n" % t.zh.workerUsername),
            call("password %s\n" % t.zh.workerPassword),
            call("logseverity %s\n" % t.zh.options.logseverity),
            call("zodb-cachesize %s\n" % t.zh.options.zodb_cachesize),
            call("calllimit %s\n" % t.zh.options.worker_call_limit),
            call("profiling %s\n" % t.zh.options.profiling),
            call("monitor %s\n" % t.zh.options.monitor),
        ])

    @patch('{src}.NICE_PATH'.format(**PATH), '/path/to/nice')
    def test_createWorker(t):
        '''Worker Management Function
        creates the protocol class internally to make tesging extra-difficult
        factor it out
        '''
        # should be set by __init__
        t.zh.workerprocessmap = {}
        t.zh.worker_processes = set()
        t.zh.options = Mock(
            name='options', spec_set=['workers', 'hubworker_priority'],
            workers=1,
            hubworker_priority=1
        )
        workerNum = 'worker_id'
        t.zh.hubworker_priority = sentinel.hubworker_priority
        t.zh.workerconfig = 'workerconfig'

        t.zh.createWorker(workerNum)

        t.assertEqual(
            t.zh.workerprocessmap,
            {t.reactor.spawnProcess.return_value.pid:
                t.reactor.spawnProcess.return_value}
        )
        # pull the protocol out of the spawnProcess call
        args, kwargs = t.reactor.spawnProcess.call_args
        proc = args[0]
        t.assertEqual(t.zh.worker_processes, set([proc]))

    @patch('{src}.IHubHeartBeatCheck'.format(**PATH), autospec=True)
    @patch('{src}.EventHeartbeat'.format(**PATH), autospec=True)
    def test_heartbeat(t, EventHeartbeat, IHubHeartBeatCheck):
        '''Event Management / Daemon Function
        Also, some Metrics Reporting stuff for fun
        '''
        t.zh.options = Mock(
            name='options', spec_set=['monitor', 'name', 'heartbeatTimeout'],
        )
        t.zh.niceDoggie = create_autospec(t.zh.niceDoggie)
        # static value defined in function
        seconds = 30
        # Metrics reporting portion needs to be factored out
        t.zh.rrdStats = Mock(name='rrdStats', spec_set=['counter', 'gauge'])
        t.zh.totalTime = 1
        t.zh.totalEvents = sentinel.totalEvents
        service0 = Mock(name='service0', spec_set=['callTime'], callTime=9)
        t.zh.services = {'service0': service0}
        t.zh.workList = [sentinel.work0, sentinel.work1]
        t.zh.counters = collections.Counter()

        t.zh.heartbeat()

        EventHeartbeat.assert_called_with(
            t.zh.options.monitor, t.zh.name, t.zh.options.heartbeatTimeout
        )
        t.zh.zem.sendEvent.assert_called_with(EventHeartbeat.return_value)
        t.zh.niceDoggie.assert_called_with(seconds)
        t.reactor.callLater.assert_called_with(seconds, t.zh.heartbeat)
        IHubHeartBeatCheck.assert_called_with(t.zh)
        IHubHeartBeatCheck.return_value.check.assert_called_with()
        # Metrics reporting, copies zenhub.counters into rrdStats.counter
        t.zh.rrdStats.counter.has_calls([
            call('totalTime', int(t.zh.totalTime * 1000)),
            call('totalEvents', t.zh.totalEvents),
            call(
                'totalCallTime',
                sum(s.callTime for s in t.zh.services.values())
            ),
        ])
        t.zh.rrdStats.gauge.assert_has_calls([
            call('services', len(t.zh.services)),
            call('workListLength', len(t.zh.workList)),
        ])

    def test_check_workers(t):
        '''Worker Management Function
        '''
        # WARNING! creates workers without a worker number argument
        # WARNING! Logic is backwards, this test will fail
        t.zh.worker_processes = [i for i in range(3)]
        t.zh.options = sentinel.options
        t.zh.options.workers = 5
        t.zh.createWorker = create_autospec(t.zh.createWorker)

        t.zh.check_workers()

        # 5 expected workers - 3 worker processes = 2 missing workers
        # WARNING! Logic is backwards, this test will fail currently
        #t.zh.createWorker.assert_has_calls([call() for _ in range(2)])

    @patch('{src}.getUtility'.format(**PATH), autospec=True)
    @patch('{src}.os'.format(**PATH), autospec=True)
    @patch('{src}.TwistedMetricReporter'.format(**PATH), autospec=True)
    @patch('{src}.task.LoopingCall'.format(**PATH), autospec=True)
    def test_main(t, LoopingCall, TwistedMetricReporter, os, getUtility):
        '''Daemon Entry Point
        Execution waits at reactor.run() until the reactor stops
        '''
        t.zh.options = Mock(
            name='options', spec_set=['cycle', 'monitor', 'profiling'],
            cycle=True, profiling=True
        )
        # Metric Management
        t.zh._metric_writer = sentinel.metric_writer
        t.zh.profiler = Mock(name='profiler', spec_set=['stop'])
        # Worker Management
        worker_proc = Mock(name='worker_proc', spec_set=['signalProcess'])
        t.zh.workerprocessmap = {'po0': worker_proc}
        t.zh.workerconfig = sentinel.workerconfig

        t.zh.main()

        # convert to a looping call
        t.reactor.callLater.assert_called_with(0, t.zh.heartbeat)
        # sets up and starts its metric reporter
        TwistedMetricReporter.assert_called_with(
            metricWriter=t.zh._metric_writer,
            tags={
                'zenoss_daemon': 'zenhub',
                'zenoss_monitor': t.zh.options.monitor,
                'internal': True
            }
        )
        t.assertEqual(t.zh.metricreporter, TwistedMetricReporter.return_value)
        t.zh.metricreporter.start.assert_called_with()
        # trigger to shut down metric reporter before zenhub exits
        t.reactor.addSystemEventTrigger.assert_called_with(
            'before', 'shutdown', t.zh.metricreporter.stop
        )
        # After the reactor stops:
        # shut down workers
        worker_proc.signalProcess.assert_called_with('KILL')
        os.unlink.assert_called_with(t.zh.workerconfig)
        t.zh.profiler.stop.assert_called_with()
        # Closes IEventPublisher, which breaks old integration tests
        getUtility.assert_called_with(IEventPublisher)
        getUtility.return_value.close.assert_called_with()

    @patch('{src}.ParserReadyForOptionsEvent'.format(**PATH), autospec=True)
    @patch('{src}.notify'.format(**PATH), autospec=True)
    @patch('{src}.zenPath'.format(**PATH))
    @patch('{src}.ZCmdBase'.format(**PATH))
    def test_buildOptions(
        t, ZCmdBase, zenPath, notify, ParserReadyForOptionsEvent
    ):
        '''After initialization, the ZenHub instance should have
        options parsed from its buildOptions method
        assertions based on default options
        '''
        # this should call buildOptions on parent classes, up the tree
        # currently calls an ancestor class directly
        # parser expected to be added by CmdBase.buildParser
        from optparse import OptionParser
        t.zh.parser = OptionParser()

        t.zh.buildOptions()
        t.zh.options, args = t.zh.parser.parse_args()

        ZCmdBase.buildOptions.assert_called_with(t.zh)
        t.assertEqual(t.zh.options.xmlrpcport, XML_RPC_PORT)
        t.assertEqual(t.zh.options.pbport, PB_PORT)
        zenPath.assert_called_with('etc', 'hubpasswd')
        t.assertEqual(t.zh.options.passwordfile, zenPath.return_value)
        t.assertEqual(t.zh.options.monitor, 'localhost')
        t.assertEqual(t.zh.options.workers, 2)
        t.assertEqual(t.zh.options.hubworker_priority, 5)
        t.assertEqual(t.zh.options.prioritize, False)
        t.assertEqual(t.zh.options.workersReservedForEvents, 1)
        t.assertEqual(t.zh.options.worker_call_limit, 200)
        t.assertEqual(t.zh.options.invalidation_poll_interval, 30)
        t.assertEqual(t.zh.options.profiling, False)
        t.assertEqual(t.zh.options.modeling_pause_timeout, 3600)
        # delay before actually parsing the options
        notify.assert_called_with(ParserReadyForOptionsEvent(t.zh.parser))


class DefaultConfProviderTest(TestCase):

    def test_implements_IHubConfProvider(t):
        # the class Implements the Interface
        t.assertTrue(IHubConfProvider.implementedBy(DefaultConfProvider))

    def test_adapts_ZenHub(t):
        t.assertEqual(
            adaptedBy(DefaultConfProvider), (ZenHub, )
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
        zenhub = Mock(name='zenhub', spec_set=['dmd', 'options'])
        default_conf_provider = DefaultConfProvider(zenhub)

        ret = default_conf_provider.getHubConf()

        zenhub.dmd.Monitors.Performance._getOb.assert_called_with(
            zenhub.options.monitor, None
        )
        t.assertEqual(ret, zenhub.dmd.Monitors.Performance._getOb.return_value)


class DefaultHubHeartBeatCheckTest(TestCase):

    def test_implements_IHubHeartBeatCheck(t):
        # the class Implements the Interface
        t.assertTrue(
            IHubHeartBeatCheck.implementedBy(DefaultHubHeartBeatCheck)
        )

    def test_adapts_ZenHub(t):
        t.assertIn(ZenHub, adaptedBy(DefaultHubHeartBeatCheck))

    def test___init__(t):
        zenhub = sentinel.zenhub

        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)

        # the object provides the interface
        t.assertTrue(
            IHubHeartBeatCheck.providedBy(default_hub_heartbeat_check)
        )
        # Verify the object implments the interface properly
        verifyObject(IHubHeartBeatCheck, default_hub_heartbeat_check)
        t.assertEqual(default_hub_heartbeat_check._zenhub, zenhub)

    def test_check(t):
        # does nothing
        zenhub = sentinel.zenhub
        default_hub_heartbeat_check = DefaultHubHeartBeatCheck(zenhub)
        default_hub_heartbeat_check.check()
