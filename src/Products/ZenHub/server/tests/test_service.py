##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase

import attr

from mock import Mock, patch, call, MagicMock, sentinel
from zope.interface.verify import verifyObject

from Products.ZenHub.errors import RemoteException

from ..events import IServiceAddedEvent
from ..exceptions import UnknownServiceError
from ..service import (
    ServiceManager,
    ServiceRegistry,
    ServiceLoader,
    ServiceCall,
    ServiceReference,
    ServiceReferenceFactory,
    WorkerInterceptor,
    ServiceAddedEvent,
    RemoteBadMonitor,
    pb,
    defer,
)

PATH = {"src": "Products.ZenHub.server.service"}


class ServiceCallTest(TestCase):
    """Test the ServiceCall class."""

    def setUp(self):
        self.monitor = "monitor"
        self.service = "name"
        self.method = "method"
        self.args = []
        self.kwargs = {}
        self.call = ServiceCall(
            monitor=self.monitor,
            service=self.service,
            method=self.method,
            args=self.args,
            kwargs=self.kwargs,
        )

    def test_nominal_initialization(self):
        self.assertEqual(self.call.service, self.service)
        self.assertEqual(self.call.monitor, self.monitor)
        self.assertEqual(self.call.method, self.method)
        self.assertEqual(self.call.args, self.args)
        self.assertEqual(self.call.kwargs, self.kwargs)
        self.assertTrue(hasattr(self.call, "id"))
        self.assertIsNotNone(self.call.id)

    def test_extra_arg_initialization(self):
        with self.assertRaises(TypeError):
            ServiceCall(
                monitor="monitor",
                service="name",
                method="method",
                args=(),
                kwargs={},
                extra="crashing the party",
            )

    def test_dict_conversion(self):
        expected = {
            "service": self.service,
            "monitor": self.monitor,
            "method": self.method,
            "args": self.args,
            "kwargs": self.kwargs,
        }
        dmap = attr.asdict(self.call)
        _id = dmap.pop("id", None)
        self.assertIsNotNone(_id)
        self.assertDictEqual(expected, dmap)


class ServiceManagerTest(TestCase):
    """Test the ServiceManager class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.getUtility_patcher = patch(
            "{src}.getUtility".format(**PATH),
            autospec=True,
        )
        self.getUtility = self.getUtility_patcher.start()
        self.addCleanup(self.getUtility_patcher.stop)

        self.dmd = Mock()
        self.dmd_factory = self.getUtility.return_value
        self.dmd_factory.return_value = self.dmd

        self.refclass = Mock()
        self.routes = Mock()
        self.executors = Mock()
        self.registry = ServiceRegistry()
        self.loader = MagicMock(ServiceLoader)
        self.factory = MagicMock(ServiceReferenceFactory)
        self.manager = ServiceManager(self.registry, self.loader, self.factory)

    @patch("{src}.ServiceAddedEvent".format(**PATH), spec=True)
    @patch("{src}.notify".format(**PATH), spec=True)
    def test_getService(self, notify, addedEvent):
        _getOb = self.dmd.Monitors.Performance._getOb
        _getOb.return_value = True

        name = "service"
        monitor = "localhost"
        serviceClass = self.loader.return_value
        expected_service = self.factory.return_value

        actual_service = self.manager.getService(name, monitor)

        _getOb.assert_called_once_with(monitor, False)
        self.loader.assert_called_once_with(self.dmd, monitor, name)
        self.factory.assert_called_once_with(serviceClass, name, monitor)

        addedEvent.assert_called_once_with(name, monitor)
        notify.assert_called_once_with(addedEvent.return_value)
        self.assertIs(expected_service, actual_service)

    def test_getService_bad_monitor(self):
        self.dmd.Monitors.Performance._getOb.return_value = False
        name = "service"
        monitor = "bad"

        with self.assertRaisesRegexp(RemoteBadMonitor, ".*bad.*"):
            self.manager.getService(name, monitor)

    @patch("{src}.ServiceAddedEvent".format(**PATH), spec=True)
    @patch("{src}.notify".format(**PATH), spec=True)
    def test_getService_unknown_service(self, notify, serviceAdded):
        self.dmd.Monitors.Performance._getOb.return_value = True
        name = "service"
        monitor = "localhost"
        self.loader.side_effect = UnknownServiceError(name)

        with self.assertRaisesRegexp(UnknownServiceError, ".*service.*"):
            self.manager.getService(name, monitor)

        self.loader.assert_called_once_with(self.dmd, monitor, name)
        self.factory.assert_not_called()
        serviceAdded.assert_not_called()
        notify.assert_not_called()

    @patch("{src}.ServiceAddedEvent".format(**PATH), spec=True)
    @patch("{src}.notify".format(**PATH), spec=True)
    def test_getService_bad_service(self, notify, serviceAdded):
        self.dmd.Monitors.Performance._getOb.return_value = True
        name = "service"
        monitor = "localhost"

        name = "service"
        monitor = "localhost"
        serviceClass = self.loader.return_value
        self.factory.side_effect = ValueError("boom")

        with self.assertRaises(ValueError):
            self.manager.getService(name, monitor)

        self.loader.assert_called_once_with(self.dmd, monitor, name)
        self.factory.assert_called_once_with(serviceClass, name, monitor)
        serviceAdded.assert_not_called()
        notify.assert_not_called()


class ServiceRegistryTest(TestCase):
    """Test the ServiceRegistry class."""

    def setUp(t):
        t.registry = ServiceRegistry()

    def test_get_wrong_arg_count(t):
        with t.assertRaises(TypeError):
            t.registry.get("foo")
        with t.assertRaises(TypeError):
            t.registry.get(("foo", "bar"))

    def test_add_wrong_arg_count(t):
        with t.assertRaises(TypeError):
            t.registry.add("foo", object())
        with t.assertRaises(TypeError):
            t.registry.add(("foo", "bar"), object())

    def test_api(t):
        svc = object()
        monitor = "foo"
        name = "bar"

        t.registry.add(monitor, name, svc)
        t.assertIn((monitor, name), t.registry)
        t.assertEqual(svc, t.registry.get(monitor, name))
        t.assertEqual(svc, t.registry[monitor, name])
        t.assertEqual(1, len(t.registry))
        t.assertSequenceEqual([(monitor, name)], list(t.registry))
        t.assertEqual(10, t.registry.get("bar", "baz", default=10))


class ServiceReferenceFactoryTest(TestCase):
    """Test the ServiceReferenceFactory class."""

    def setUp(self):
        self.executors = Mock()
        self.routes = Mock()
        self.target = Mock()
        self.factory = ServiceReferenceFactory(
            self.target,
            self.routes,
            self.executors,
        )

    def test_build(self):
        monitor = "localhost"
        name = "service"
        service = Mock()

        expected = self.target.return_value
        actual = self.factory(service, name, monitor)

        self.assertEqual(expected, actual)
        self.target.assert_called_once_with(
            service,
            name,
            monitor,
            routes=self.routes,
            executors=self.executors,
        )


class ServiceReferenceTest(TestCase):
    """Test the ServiceReference class."""

    def setUp(self):
        self.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        self.getLogger = self.getLogger_patcher.start()
        self.addCleanup(self.getLogger_patcher.stop)

        self.service = Mock()
        self.name = "service"
        self.monitor = "monitor"
        self.routes = Mock()
        self.executors = Mock()
        self.reference = ServiceReference(
            self.service,
            self.name,
            self.monitor,
            self.routes,
            self.executors,
        )
        self.reference.perspective = sentinel.perspective

        self.broker = Mock()
        self.broker.unserialize.side_effect = lambda d: d
        self.broker.serialize.side_effect = lambda d, p: d

    def test_service_property(self):
        self.assertEqual(self.service, self.reference.service)

    def test_remoteMessageReceived_no_route(self):
        method = "method"
        args = []
        kwargs = {}

        self.routes.get.return_value = None

        handler = Mock()
        dfr = self.reference.remoteMessageReceived(
            self.broker,
            method,
            args,
            kwargs,
        )
        dfr.addErrback(handler)
        _, args, _ = handler.mock_calls[0]
        error = args[0]

        self.assertIsInstance(error.value, pb.Error)
        self.assertRegexpMatches(
            str(error.value),
            "No route found service=service method=method",
        )

    def test_remoteMessageReceived_no_executor(self):
        method = "method"
        args = []
        kwargs = {}

        self.routes.get.return_value = "blah"
        self.executors.get.return_value = None

        handler = Mock()
        dfr = self.reference.remoteMessageReceived(
            self.broker,
            method,
            args,
            kwargs,
        )
        dfr.addErrback(handler)
        _, args, _ = handler.mock_calls[0]
        error = args[0]

        self.assertIsInstance(error.value, pb.Error)
        self.assertEqual(
            str(error.value),
            "Internal ZenHub error: (KeyError) "
            "'Executor not registered executor=blah "
            "service=service method=method'",
        )

    def test_remoteMessageReceived(self):
        method = "method"
        args = []
        kwargs = {}

        executor = Mock(spec=["submit"])
        result = executor.submit.return_value
        self.routes.get.return_value = "blah"
        self.executors.get.return_value = executor

        dfr = self.reference.remoteMessageReceived(
            self.broker,
            method,
            args,
            kwargs,
        )

        self.assertIs(result, dfr.result)
        self.assertEqual(1, executor.submit.call_count)

    def test_remoteMessageReceived_raise_external_error(self):
        args = []
        kwargs = {}

        executor = Mock(spec=["submit"])
        self.routes.get.return_value = "blah"
        self.executors.get.return_value = executor

        exceptions = [
            pb.Error(ValueError("boom")),
            pb.RemoteError("ValueError", "boom", "[no traceback]"),
            RemoteException("boom", "tb"),
        ]
        for expected_ex in exceptions:
            executor.submit.side_effect = lambda j, ex=expected_ex: defer.fail(
                ex
            )
            cb = Mock()
            dfr = self.reference.remoteMessageReceived(
                self.broker,
                "method",
                args,
                kwargs,
            )
            dfr.addErrback(cb)

            try:
                self.broker.unserialize.assert_has_calls(
                    [
                        call(args),
                        call(kwargs),
                    ]
                )
                self.broker.serialize.assert_not_called()
                self.assertTrue(cb.called)
                self.assertEqual(1, cb.call_count)
                error = cb.call_args[0][0]
                self.assertEqual(expected_ex, error.value)
            except Exception as ex:
                ex.args = (ex.args[0] + " [exception=%r]" % (expected_ex,),)
                raise

    def test_remoteMessageReceived_raise_exception(self):
        args = []
        kwargs = {}
        ex = ValueError("boom")
        executor = Mock(spec=["submit"])
        executor.submit.side_effect = lambda j: defer.fail(ex)
        self.routes.get.return_value = "blah"
        self.executors.get.return_value = executor

        dfr = self.reference.remoteMessageReceived(
            self.broker,
            "method",
            args,
            kwargs,
        )
        dfr.addErrback(lambda f: (f.trap(pb.Error), f))
        exType, failure = dfr.result

        self.broker.unserialize.assert_has_calls(
            [
                call(args),
                call(kwargs),
            ]
        )
        self.broker.serialize.assert_not_called()
        self.assertIs(exType, pb.Error)
        self.assertEqual(
            "Internal ZenHub error: (ValueError) boom",
            str(failure.value),
        )


class WorkerInterceptorTest(TestCase):
    """Test the WorkerInterceptor class."""

    def test_derivation(self):
        # Verify that WorkerInterceptor derives from ServiceReference
        self.assertTrue(
            issubclass(WorkerInterceptor, ServiceReference),
            "WorkerInterceptor does not derive from ServiceReference",
        )

    def test_no_extra_code(self):
        expected = {"__doc__", "__module__"}
        actual = set(WorkerInterceptor.__dict__)
        self.assertSetEqual(
            expected,
            actual,
            "Add functionality to ServiceReference, not WorkerInterceptor",
        )


class ServiceAddedEventTest(TestCase):
    """Test the ServiceAddedEvent class."""

    def test___init__(t):
        name, instance = "name", "instance"
        service_added_event = ServiceAddedEvent(name, instance)
        # the class Implements the Interface
        t.assertTrue(IServiceAddedEvent.implementedBy(ServiceAddedEvent))
        # the object provides the interface
        t.assertTrue(IServiceAddedEvent.providedBy(service_added_event))
        # Verify the object implments the interface properly
        verifyObject(IServiceAddedEvent, service_added_event)

        t.assertEqual(service_added_event.name, name)
        t.assertEqual(service_added_event.instance, instance)
