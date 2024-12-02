##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase

from mock import MagicMock, patch
from twisted.internet import defer
from twisted.python.failure import Failure

from ..service import ServiceCall
from ..worker import pb, ServiceRegistry, Worker

PATH = {"src": "Products.ZenHub.server.worker"}


class WorkerTest(TestCase):
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.name = "default_0"
        t.remote = MagicMock(pb.RemoteReference, autospec=True)
        t.worker = Worker(name=t.name, remote=t.remote)

    def test_properties(t):
        t.assertEqual(t.worker.remote, t.remote)
        t.assertEqual(t.worker.name, t.name)
        t.assertIsInstance(t.worker.services, ServiceRegistry)

    def test_uncached_service_reference(t):
        service = MagicMock(pb.RemoteReference, autospect=True)
        t.remote.callRemote.return_value = defer.succeed(service)
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[],
            kwargs={},
        )
        expected_result = service.callRemote.return_value

        dfr = t.worker.run(call)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, expected_result)
        t.remote.callRemote.assert_called_once_with(
            "getService", call.service, call.monitor
        )
        service.callRemote.assert_called_once_with(call.method)

        cached_service = t.worker.services.get("localhost", "service")
        t.assertEqual(cached_service, service)

    def test_cached_service_reference(t):
        service_ref = MagicMock(pb.RemoteReference, autospect=True)
        monitor = "localhost"
        service_name = "service"
        t.worker.services.add(monitor, service_name, service_ref)
        call = ServiceCall(
            monitor=monitor,
            service=service_name,
            method="method",
            args=[],
            kwargs={},
        )
        expected_result = service_ref.callRemote.return_value

        dfr = t.worker.run(call)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, expected_result)
        t.remote.callRemote.assert_not_called()
        service_ref.callRemote.assert_called_once_with(call.method)

    def test_run_method_with_args(t):
        service_ref = MagicMock(pb.RemoteReference, autospect=True)
        monitor = "localhost"
        service_name = "service"
        t.worker.services.add(monitor, service_name, service_ref)
        call = ServiceCall(
            monitor=monitor,
            service=service_name,
            method="method",
            args=["arg"],
            kwargs={"arg": 1},
        )
        expected_result = service_ref.callRemote.return_value

        dfr = t.worker.run(call)

        t.assertIsInstance(dfr, defer.Deferred)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, expected_result)
        service_ref.callRemote.assert_called_once_with(
            call.method,
            call.args[0],
            arg=call.kwargs["arg"],
        )

    def test_bad_service(t):
        expected_error = ValueError("boom")
        t.remote.callRemote.side_effect = expected_error
        call = ServiceCall(
            monitor="localhost",
            service="the_service",
            method="method",
            args=[],
            kwargs={},
        )

        dfr = t.worker.run(call)

        t.assertIsInstance(dfr.result, Failure)

        actual_error = dfr.result.value
        t.assertIsInstance(actual_error, ValueError)
        t.assertIs(actual_error, expected_error)

        # add an errback to silence the unhandled deferred error message
        dfr.addErrback(lambda x: None)

    def test_remote_method_failure(t):
        service_ref = MagicMock(pb.RemoteReference, autospect=True)
        monitor = "localhost"
        service_name = "service"
        expected_error = ValueError("boom")
        service_ref.callRemote.side_effect = expected_error
        t.worker.services.add(monitor, service_name, service_ref)
        call = ServiceCall(
            monitor="localhost",
            service="service",
            method="method",
            args=[],
            kwargs={},
        )

        dfr = t.worker.run(call)

        service_ref.callRemote.assert_called_once_with(call.method)
        t.assertIsInstance(dfr.result, Failure)
        actual_error = dfr.result.value
        t.assertIsInstance(actual_error, ValueError)
        t.assertIs(actual_error, expected_error)

        # add an errback to silence the unhandled deferred error message
        dfr.addErrback(lambda x: None)
