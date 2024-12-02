##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from unittest import TestCase

from mock import call, MagicMock, Mock, patch, sentinel
from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from Products.ZenHub.zenhubclient import HubDown, ZenHubClient

PATH = {"src": "Products.ZenHub.zenhubclient"}


class DisableLoggerLayer(object):
    @classmethod
    def setUp(self):
        logging.disable(logging.CRITICAL)


class BrokerSimulator(object):
    """Simulates a twisted.spread 'broker' object."""

    def __init__(self):
        self.transport = Mock(spec=["socket"])
        self.factory = Mock(spec=["login"])
        self.callback = None

    def notifyOnDisconnect(self, callback):
        self.callback = callback


class ClientServiceSimulator(object):
    """Simulates a twisted.application.internet.ClientService object."""

    def __init__(self, endpoint, factory, retryPolicy, prepareConnection):
        self.endpoint = endpoint
        self.factory = factory
        self.policy = retryPolicy
        self.prepare_connection = prepareConnection
        self.broker = BrokerSimulator()
        self.deferred = defer.Deferred()

    def startService(self):
        self.prepare_connection(self.broker)

    def stopService(self):
        pass

    def whenConnected(self):
        return self.deferred


class ZenHubClientTest(TestCase):
    """Test the ZenHubClient class."""

    layer = DisableLoggerLayer

    def setUp(t):
        t.reactor = Mock(reactor, autospec=True)
        t.endpoint = sentinel.endpoint
        t.credentials = Mock()
        t.app = Mock()
        t.timeout = 10
        t.worklistId = "default"
        t.zenhubref = Mock()
        t.broker = BrokerSimulator()
        t.startd = defer.Deferred()
        t.stopd = defer.Deferred()
        t.instanceId = "zenhub"

        # Patch external dependencies
        needs_patching = [
            "ClientService",
            "setKeepAlive",
            "ZenPBClientFactory",
        ]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                "{src}.{target}".format(target=target, **PATH),
                autospec=True,
            )
            t.patchers[target] = patched
            name = target.rpartition(".")[-1]
            setattr(t, name, patched.start())
            t.addCleanup(patched.stop)

        t.client = t.ClientService.return_value
        t.client.whenConnected.return_value = t.startd

        t.zhc = ZenHubClient(
            t.app,
            t.endpoint,
            t.credentials,
            t.timeout,
            reactor=t.reactor,
        )

        def _stopService():
            t.zhc._disconnected()
            return t.stopd

        init_args = list(t.ClientService.call_args)[1]
        callback = init_args["prepareConnection"]
        t.client.startService.side_effect = lambda: callback(t.broker)
        t.client.stopService.side_effect = _stopService
        t.broker.factory.login.return_value = defer.succeed(t.zenhubref)
        t.zenhubref.callRemote.return_value = defer.succeed(t.instanceId)

    def test_initial_state(t):
        t.assertFalse(t.zhc.is_connected)
        t.assertIsNone(t.zhc.instance_id)
        t.assertEqual(len(t.zhc.services), 0)

    def test_start(t):
        d = t.zhc.start()

        t.assertIs(d, t.startd)
        t.assertTrue(t.zhc.is_connected)
        t.assertEqual(t.zhc.instance_id, t.instanceId)
        t.assertEqual(len(t.zhc.services), 0)

    def test_stop_without_start(t):
        d = t.zhc.stop()

        t.assertIs(d, t.stopd)
        t.assertFalse(t.zhc.is_connected)
        t.assertEqual(len(t.zhc.services), 0)

    def test_stop_after_start(t):
        _ = t.zhc.start()
        d = t.zhc.stop()

        t.assertIs(d, t.stopd)
        t.assertFalse(t.zhc.is_connected)
        t.assertEqual(len(t.zhc.services), 0)

    def test_when_connected(t):
        cb1 = MagicMock()
        cb2 = MagicMock()
        t.zhc.notify_on_connect(cb1)
        t.zhc.notify_on_connect(cb2)

        _ = t.zhc.start()

        t.assertTrue(cb1.called)
        t.assertTrue(cb2.called)

    def test_when_disconnected(t):
        cb1 = MagicMock()
        cb2 = MagicMock()
        t.zhc.notify_on_disconnect(cb1)
        t.zhc.notify_on_disconnect(cb2)

        _ = t.zhc.start()
        _ = t.zhc.stop()

        t.assertTrue(cb1.called)
        t.assertTrue(cb2.called)

    def test_ping_without_start(t):
        d = t.zhc.ping()

        t.assertIsInstance(d.result, Failure)
        t.assertIsInstance(d.result.value, HubDown)

        # silence 'Unhandled error in Deferred'
        d.addErrback(lambda x: None)

    def test_register_worker_without_start(t):
        d = t.zhc.register_worker("a", "b", "c")  # arg values don't matter

        t.assertIsInstance(d.result, Failure)
        t.assertIsInstance(d.result.value, HubDown)

        # silence 'Unhandled error in Deferred'
        d.addErrback(lambda x: None)

    def test_unregister_worker_without_start(t):
        d = t.zhc.unregister_worker("a", "b")  # arg values don't matter

        t.assertIsInstance(d.result, Failure)
        t.assertIsInstance(d.result.value, HubDown)

        # silence 'Unhandled error in Deferred'
        d.addErrback(lambda x: None)

    def test_get_service_without_start(t):
        d = t.zhc.get_service("a", "b", "c", {})  # arg values don't matter

        t.assertIsInstance(d.result, Failure)
        t.assertIsInstance(d.result.value, HubDown)

        # silence 'Unhandled error in Deferred'
        d.addErrback(lambda x: None)

    def test_ping(t):
        t.zhc.start()
        t.zenhubref.callRemote.return_value = defer.succeed("pong")

        d = t.zhc.ping()

        last_call = t.zenhubref.callRemote.call_args_list[-1]
        name, _ = last_call
        t.assertEqual(name[0], "ping")
        t.assertEqual("pong", d.result)

    def test_register_worker(t):
        t.zhc.start()
        t.zenhubref.callRemote.return_value = defer.succeed(None)
        worker = Mock()
        workerId = "default_0"
        worklistId = "default"

        t.zhc.register_worker(worker, workerId, worklistId)

        last_call = t.zenhubref.callRemote.call_args_list[-1]
        expected = call(
            "reportForWork", worker, name=workerId, worklistId=worklistId
        )
        t.assertEqual(last_call, expected)

    def test_unregister_worker(t):
        t.zhc.start()
        t.zenhubref.callRemote.return_value = defer.succeed(None)
        workerId = "default_0"
        worklistId = "default"

        t.zhc.unregister_worker(workerId, worklistId)

        last_call = t.zenhubref.callRemote.call_args_list[-1]
        expected = call("resignFromWork", name=workerId, worklistId=worklistId)
        t.assertEqual(last_call, expected)

    def test_get_new_service(t):
        t.zhc.start()
        service = Mock()
        t.zenhubref.callRemote.return_value = defer.succeed(service)
        name = "Products.ZenCollector.services.ConfigService.ConfigService"
        monitor = "localhost"
        listener = Mock()
        options = {}

        d = t.zhc.get_service(name, monitor, listener, options)

        last_call = t.zenhubref.callRemote.call_args_list[-1]
        expected = call("getService", name, monitor, listener, options)
        t.assertEqual(last_call, expected)
        t.assertEqual(d.result, service)
        t.assertIn(name, t.zhc.services)
        t.assertEqual(t.zhc.services[name], service)

    def test_get_cached_service(t):
        t.zhc.start()
        name = "PingPerformance"
        service = Mock()
        t.zhc._services[name] = service
        monitor = "localhost"
        listener = Mock()
        options = {}

        d = t.zhc.get_service(name, monitor, listener, options)

        t.zenhubref.callRemote.assert_called_once_with("getHubInstanceId")
        t.assertEqual(d.result, service)
