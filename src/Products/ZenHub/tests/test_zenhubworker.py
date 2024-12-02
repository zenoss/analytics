##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import sys

from mock import patch, sentinel, call, Mock, create_autospec, ANY
from unittest import TestCase

from Products.ZenHub.zenhubworker import (
    _CumulativeWorkerStats,
    ContinuousProfiler,
    IDLE,
    IMetricManager,
    pb,
    PB_PORT,
    RemoteBadMonitor,
    ServiceReference,
    ServiceReferenceFactory,
    UnknownServiceError,
    ZCmdBase,
    ZENHUB_MODULE,
    ZenHubWorker,
)

PATH = {"src": "Products.ZenHub.zenhubworker"}


class ZenHubWorkerTest(TestCase):
    """Test the ZenHubWorker class."""

    def setUp(t):
        # Patch out the ZCmdBase __init__ method
        t.ZCmdBase_patcher = patch.object(
            ZCmdBase,
            "__init__",
            autospec=True,
            return_value=None,
        )
        t.ZCmdBase__init__ = t.ZCmdBase_patcher.start()
        t.addCleanup(t.ZCmdBase_patcher.stop)

        # Mock out attributes set by ZCmdBase
        t.zcmdbase_patchers = {
            "dmd": patch.object(ZenHubWorker, "dmd", create=True),
            "log": patch.object(ZenHubWorker, "log", create=True),
            "options": patch.object(ZenHubWorker, "options", create=True),
            "connection": patch.object(
                ZenHubWorker, "connection", create=True
            ),
        }
        for name, patcher in t.zcmdbase_patchers.items():
            setattr(t, name, patcher.start())
            t.addCleanup(patcher.stop)

        # Set ZenHubWorker's options to some real and mock values
        t.options.profiling = True
        t.options.hubhost = "localhost"
        t.options.hubport = 8765
        t.options.hubusername = sentinel.hubusername
        t.options.hubpassword = sentinel.hubpassword
        t.options.workerid = sentinel.workerid
        t.options.monitor = sentinel.monitor
        t.options.localport = 12345

        # Patch external dependencies
        needs_patching = [
            "clientFromString",
            "getGlobalSiteManager",
            "loadPlugins",
            "load_config",
            "reactor",
            "ContinuousProfiler",
            "MetricManager",
            "Metrology",
            "PingZenHub",
            "ServiceLoader",
            "ServiceManager",
            "ServiceReferenceFactory",
            "ServiceRegistry",
            "UsernamePassword",
            "ZenHubClient",
            "serverFromString",
            "LocalServer",
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

        # A little cheat; 'worklistId' and 'instanceId' are set by the
        # parseOptions method, but parseOptions is called by ZenHubWorker's
        # base class, which has been mocked out.  So worklistId and
        # instanceId are set on the class so it's available to the instance.
        ZenHubWorker.worklistId = "default"
        ZenHubWorker.instanceId = "%s_%s" % (
            ZenHubWorker.worklistId,
            t.options.workerid,
        )

        t.zhw = ZenHubWorker(t.reactor)

    def test___init__(t):
        t.ZCmdBase__init__.assert_called_with(t.zhw)

        t.load_config.assert_called_with("hubworker.zcml", ZENHUB_MODULE)
        # Optional Profiling
        t.ContinuousProfiler.assert_called_with("ZenHubWorker", log=t.zhw.log)
        t.assertEqual(t.zhw.profiler, t.ContinuousProfiler.return_value)
        t.zhw.profiler.start.assert_called_with()
        t.reactor.addSystemEventTrigger.assert_called_once_with(
            "before",
            "shutdown",
            t.zhw.profiler.stop,
        )

        t.assertEqual(t.zhw.current, IDLE)
        t.assertEqual(t.zhw.currentStart, 0)
        t.Metrology.meter.assert_called_with("zenhub.workerCalls")
        t.assertEqual(t.zhw.numCalls, t.Metrology.meter.return_value)

        t.assertEqual(t.zhw.zem, t.zhw.dmd.ZenEventManager)
        t.loadPlugins.assert_called_with(t.zhw.dmd)

        t.ServiceRegistry.assert_called_once_with()
        t.ServiceLoader.assert_called_once_with()
        t.ServiceReferenceFactory.assert_called_once_with(t.zhw)
        t.ServiceManager.assert_called_once_with(
            t.ServiceRegistry.return_value,
            t.ServiceLoader.return_value,
            t.ServiceReferenceFactory.return_value,
        )

        t.UsernamePassword.assert_called_once_with(
            t.zhw.options.hubusername,
            t.zhw.options.hubpassword,
        )
        t.clientFromString.assert_called_once_with(
            t.reactor,
            "tcp:%s:%s" % (t.zhw.options.hubhost, t.zhw.options.hubport),
        )
        t.ZenHubClient.assert_called_once_with(
            t.zhw,
            t.clientFromString.return_value,
            t.UsernamePassword.return_value,
            t.zhw.options.hub_response_timeout,
            t.reactor,
        )
        t.assertEqual(t.ZenHubClient.return_value, t.zhw._ZenHubWorker__client)

        t.PingZenHub.assert_called_once_with(t.ZenHubClient.return_value)

        t.serverFromString.assert_called_once_with(
            t.reactor,
            "tcp:{}:interface=127.0.0.1".format(t.zhw.options.localport),
        )
        t.LocalServer.assert_called_once_with(
            t.reactor, t.serverFromString.return_value
        )
        server = t.LocalServer.return_value
        server.add_resource.assert_has_calls(
            [call("zenhub", ANY), call("stats", ANY)]
        )

        t.MetricManager.assert_called_with(
            daemon_tags={
                "zenoss_daemon": "zenhub_worker_%s_%s"
                % (
                    t.zhw.worklistId,
                    t.zhw.options.workerid,
                ),
                "zenoss_monitor": t.zhw.options.monitor,
                "internal": True,
            },
        )
        t.assertEqual(t.zhw._metric_manager, t.MetricManager.return_value)
        t.getGlobalSiteManager.assert_called_once_with()
        gsm = t.getGlobalSiteManager.return_value
        gsm.registerUtility.assert_called_once_with(
            t.zhw._metric_manager,
            IMetricManager,
            name="zenhub_worker_metricmanager",
        )

    def test_getZenHubStatus_disconnected(t):
        t.zhw._ZenHubWorker__client.is_connected = False
        t.assertEqual(t.zhw.getZenHubStatus(), "disconnected")

    def test_getZenHubStatus_connected(t):
        t.zhw._ZenHubWorker__client.is_connected = True
        t.assertEqual(t.zhw.getZenHubStatus(), "connected")

    @patch("{src}.signal".format(**PATH), autospec=True)
    def test_start(t, signal):
        signal.SIGUSR1 = sentinel.SIGUSR1
        signal.SIGUSR2 = sentinel.SIGUSR2

        t.zhw.start()

        signal.signal.assert_has_calls(
            [
                call(signal.SIGUSR1, t.zhw.sighandler_USR1),
                call(signal.SIGUSR2, t.zhw.sighandler_USR2),
            ]
        )

        t.ZenHubClient.return_value.start.assert_called_once_with()
        t.LocalServer.return_value.start.assert_called_once_with()
        t.MetricManager.return_value.start.assert_called_once_with()

        t.reactor.addSystemEventTrigger.assert_has_calls(
            [
                call("before", "shutdown", t.ZenHubClient.return_value.stop),
                call("before", "shutdown", t.PingZenHub.return_value.stop),
                call("before", "shutdown", t.LocalServer.return_value.stop),
                call("before", "shutdown", t.MetricManager.return_value.stop),
            ]
        )

    def test_audit(t):
        # Verifies the API exists, although it does nothing.
        action = sentinel.action
        t.zhw.audit(action)

    @patch("{src}.super".format(**PATH))
    def test_sighandler_USR1(t, _super):
        t.zhw.options.profiling = True
        t.zhw.profiler = Mock(ContinuousProfiler, name="profiler")
        signum, frame = sentinel.signum, sentinel.frame

        t.zhw.sighandler_USR1(signum, frame)

        t.zhw.profiler.dump_stats.assert_called_with()
        _super.assert_called_with(ZenHubWorker, t.zhw)
        _super.return_value.sighandler_USR1.assert_called_with(signum, frame)

    def test_sighandler_USR2(t):
        args = sentinel.args
        t.zhw.reportStats = create_autospec(t.zhw.reportStats)

        t.zhw.sighandler_USR2(args)

        t.zhw.reportStats.assert_called_with()

    def test__work_started(t):
        startTime = sentinel.startTime

        t.zhw._work_started(startTime)

        t.assertEqual(t.zhw.currentStart, startTime)
        t.zhw.numCalls.mark.assert_called_once_with()

    @patch("{src}.IDLE".format(**PATH))
    def test__work_finished_no_shutdown(t, idle):
        duration = sentinel.duration
        method = sentinel.method
        t.zhw.numCalls.count = 1
        t.zhw.options.call_limit = 5

        t.zhw._work_finished(duration, method)

        t.assertEqual(idle, t.zhw.current)
        t.assertEqual(0, t.zhw.currentStart)
        t.reactor.callLater.assert_not_called()

    @patch("{src}.IDLE".format(**PATH))
    def test__work_finished_with_shutdown(t, idle):
        duration = sentinel.duration
        method = sentinel.method
        t.zhw.numCalls.count = 5
        t.zhw.options.call_limit = 5

        t.zhw._work_finished(duration, method)

        t.assertEqual(idle, t.zhw.current)
        t.assertEqual(0, t.zhw.currentStart)
        t.reactor.callLater.assert_called_once_with(0, t.zhw._shutdown)

    @patch("{src}.isoDateTime".format(**PATH), autospec=True)
    @patch("{src}.time".format(**PATH), autospec=True)
    def test_reportStats(t, time, isoDateTime):
        """Test the metric reporting function.

        Log various statistics on services as a general rule, do not test
        individual log messages, just log format this function is difficult
        to read and should be refactored.
        """
        t.zhw.current = sentinel.current_job
        t.zhw.options.workerid = 1
        t.zhw.currentStart = 0
        time.time.return_value = 7
        monitor = "localhost"
        name = "module.module_name"
        service = sentinel.service
        method = "method_name"
        stats = sentinel.stats
        stats.numoccurrences = 9
        stats.totaltime = 54
        stats.lasttime = 555
        service.callStats = {method: stats}
        t.zhw._ZenHubWorker__registry = {(monitor, name): service}
        isodate = isoDateTime.return_value

        t.zhw.reportStats()

        isoDateTime.assert_called_with(stats.lasttime)

        parsed_service_id = "module_name"
        average_time = stats.totaltime / stats.numoccurrences
        headers = [
            "Service",
            "Method",
            "Count",
            "Total",
            "Average",
            "Last Run",
        ]
        t.zhw.log.info.assert_called_with(
            "Running statistics:\n"
            " {headers[0]: <50} {headers[1]: <32} {headers[2]: >8}"
            " {headers[3]: >12} {headers[4]: >8} {headers[5]}\n"
            " - {parsed_service_id: <49}{method: <32}"
            "{stats.numoccurrences: 9}{stats.totaltime: 13.2f}"
            "{average_time: 9.2f} {isodate}".format(**locals()),
        )

    def test_remote_reportStatus(t):
        t.zhw.reportStats = Mock(t.zhw.reportStats)
        t.zhw.remote_reportStatus()
        t.zhw.reportStats.assert_called_once_with()

    def test_remote_reportStatus_failure(t):
        t.zhw.reportStats = Mock(t.zhw.reportStats)
        t.zhw.reportStats.side_effect = ValueError("boom")

        t.zhw.remote_reportStatus()

        t.zhw.reportStats.assert_called_once_with()
        t.zhw.log.exception.assert_called_once_with(ANY)

    def test_remote_getService(t):
        name = "service"
        monitor = "monitor"
        manager = t.ServiceManager.return_value
        expected = manager.getService.return_value

        actual = t.zhw.remote_getService(name, monitor)

        t.assertEqual(expected, actual)
        manager.getService.assert_called_once_with(name, monitor)

    def test_remote_getService_bad_monitor(t):
        name = "service"
        monitor = "bad"
        manager = t.ServiceManager.return_value

        errorMessage = "boom"
        tb = Mock()
        manager.getService.side_effect = RemoteBadMonitor(errorMessage, tb)

        with t.assertRaises(RemoteBadMonitor):
            t.zhw.remote_getService(name, monitor)

        manager.getService.assert_called_once_with(name, monitor)

    def test_remote_getService_unknown_service(t):
        name = "bad"
        monitor = "monitor"
        manager = t.ServiceManager.return_value
        manager.getService.side_effect = UnknownServiceError("boom")

        with t.assertRaises(UnknownServiceError):
            t.zhw.remote_getService(name, monitor)

        manager.getService.assert_called_once_with(name, monitor)
        t.zhw.log.error.assert_has_calls([ANY])

    def test_remote_getService_general_error(t):
        name = "bad"
        monitor = "monitor"
        error = ValueError("boom")
        manager = t.ServiceManager.return_value
        manager.getService.side_effect = error

        with t.assertRaises(pb.Error):
            t.zhw.remote_getService(name, monitor)
            manager.getService.assert_called_once_with(name, monitor)
            t.zhw.log.exception.assert_has_calls([ANY])

    def test__shutdown(t):
        t.zhw._shutdown()
        t.reactor.stop.assert_called_with()

    @patch("{src}.ZCmdBase".format(**PATH))
    def test_buildOptions(t, ZCmdBase):
        """Test the result of the buildOptions method.

        In this isolated test, after argument parsing, the ZenHubWorker
        instance options object should have values matching the default
        values specified for the options.
        """
        # this should call buildOptions on parent classes, up the tree
        # currently calls an ancestor class directly
        # parser expected to be added by CmdBase.buildParser
        from optparse import OptionParser

        t.zhw.parser = OptionParser()
        # Given no command line arguments
        sys.argv = []

        t.zhw.buildOptions()
        t.zhw.options, args = t.zhw.parser.parse_args()

        ZCmdBase.buildOptions.assert_called_with(t.zhw)
        t.assertEqual(t.zhw.options.hubhost, "localhost")
        t.assertEqual(t.zhw.options.hubport, PB_PORT)
        t.assertEqual(t.zhw.options.hubusername, "admin")
        t.assertEqual(t.zhw.options.hubpassword, "zenoss")
        t.assertEqual(t.zhw.options.call_limit, 200)
        t.assertFalse(t.zhw.options.profiling)
        t.assertEqual(t.zhw.options.monitor, "localhost")
        t.assertEqual(t.zhw.options.workerid, 0)


class ServiceReferenceFactoryTest(TestCase):
    """Test the ServiceReferenceFactory class."""

    @patch("{src}.ServiceReference".format(**PATH), autospec=True)
    def test_build(t, ServiceReference):
        worker = sentinel.worker
        factory = ServiceReferenceFactory(worker)
        service = sentinel.service
        name = sentinel.name
        monitor = sentinel.monitor

        result = factory(service, name, monitor)

        ServiceReference.assert_called_once_with(
            service,
            name,
            monitor,
            worker,
        )
        t.assertEqual(ServiceReference.return_value, result)


class ServiceReferenceTest(TestCase):
    """Test the ServiceReference class."""

    def setUp(t):
        t._CumulativeWorkerStats_patcher = patch(
            "{src}._CumulativeWorkerStats".format(**PATH),
            autospec=True,
        )
        t._CumulativeWorkerStats = t._CumulativeWorkerStats_patcher.start()
        t.addCleanup(t._CumulativeWorkerStats_patcher.stop)

        t.service = Mock(spec_set=["remoteMessageReceived", "callTime"])
        t.worker = Mock(ZenHubWorker)
        t.name = "path.to.service"
        t.monitor = sentinel.monitor
        t.ref = ServiceReference(t.service, t.name, t.monitor, t.worker)

    def test_callStats_property(t):
        t.assertIsInstance(t.ref.callStats, dict)
        t.assertEqual(0, len(t.ref.callStats))

    def test_name_property(t):
        t.assertEqual(t.name, t.ref.name)

    def test_monitor_property(t):
        t.assertEqual(t.monitor, t.ref.monitor)

    def test_remoteMessageReceived(t):
        broker = sentinel.broker
        message = sentinel.message
        args = sentinel.args
        kwargs = sentinel.kwargs

        t.worker.async_syncdb.side_effect = [None]

        expected = t.service.remoteMessageReceived.return_value

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            d = t.ref.remoteMessageReceived(broker, message, args, kwargs)

            t.assertEqual(expected, d.result)
            p.assert_called_once_with(message)
            t.worker.async_syncdb.assert_called_once_with()
            t.service.remoteMessageReceived.assert_called_once_with(
                broker,
                message,
                args,
                kwargs,
            )

    def test_remoteMessageReceived_raises_exception(t):
        broker = sentinel.broker
        method = sentinel.method
        args = sentinel.args
        kwargs = sentinel.kwargs

        error = ValueError("boom")
        t.service.remoteMessageReceived.side_effect = error

        class Capture(object):
            result = None

            def err(self, err):
                self.result = err.trap(ValueError)

        with patch.object(t.ref, "_ServiceReference__update_stats") as p:
            t.ref.debug = True

            handler = Capture()
            d = t.ref.remoteMessageReceived(broker, method, args, kwargs)
            d.addErrback(handler.err)

            p.assert_called_once_with(method)
            t.worker.async_syncdb.assert_called_once_with()
            t.service.remoteMessageReceived.assert_called_once_with(
                broker,
                method,
                args,
                kwargs,
            )
            t.assertEqual(ValueError, handler.result)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test___update_stats(t, time):
        start = 15
        finish = 20
        time.time.side_effect = [start, finish]
        method = "method"
        expected_current = "service/method"
        stats = Mock(_CumulativeWorkerStats)
        t.service.callTime = 0

        with patch.dict(t.ref.callStats, method=stats):
            with t.ref._ServiceReference__update_stats(method) as p:
                t.assertEqual(t.service, p)
                t.assertEqual(expected_current, t.worker.current)
                t.worker._work_started.assert_called_once_with(start)

            stats.addOccurrence.assert_called_once_with(5, finish)
            t.assertEqual(5, t.service.callTime)
            t.worker._work_finished.assert_called_once_with(5, method)


class _CumulativeWorkerStatsTest(TestCase):
    """Test the _CumulativeWorkerStats class."""

    def test___init__(t):
        cws = _CumulativeWorkerStats()
        t.assertEqual(cws.numoccurrences, 0)
        t.assertEqual(cws.totaltime, 0.0)
        t.assertEqual(cws.lasttime, 0)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_addOccurrence(t, time):
        time.time.side_effect = [sentinel.t0, sentinel.t1]
        cws = _CumulativeWorkerStats()

        cws.addOccurrence(10)

        t.assertEqual(cws.numoccurrences, 1)
        t.assertEqual(cws.totaltime, 10.0)
        t.assertEqual(cws.lasttime, sentinel.t0)

        cws.addOccurrence(100)

        t.assertEqual(cws.numoccurrences, 2)
        t.assertEqual(cws.totaltime, 110.0)
        t.assertEqual(cws.lasttime, sentinel.t1)
