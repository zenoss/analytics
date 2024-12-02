##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from mock import call, Mock, NonCallableMock, patch
from twisted.internet import defer
from unittest import TestCase

from ..interface import IHubServerConfig
from ..main import (
    start_server,
    stop_server,
    make_server_factory,
    make_pools,
    make_service_manager,
    WorkerInterceptor,
    make_executors,
)
from ..utils import subTest

PATH = {"src": "Products.ZenHub.server.main"}


class StartServerTest(TestCase):
    """Test the start_server function."""

    @patch("{src}._executors".format(**PATH), autospec=True)
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}.TCPDescriptor".format(**PATH), autospec=True)
    @patch("{src}.serverFromString".format(**PATH), autospec=True)
    @patch("{src}.setKeepAlive".format(**PATH), autospec=True)
    def test_start_server(
        self,
        _setKeepAlive,
        _serverFromString,
        _tcpd,
        _getUtility,
        _executors,
    ):
        executor = Mock(spec=["start"])
        _executors.values.return_value = [executor]

        config = Mock(spec=["pbport"])
        _getUtility.return_value = config

        with_port = _tcpd.with_port
        descriptor = with_port.return_value

        server = _serverFromString.return_value
        dfr = defer.Deferred()
        server.listen.return_value = dfr

        reactor = NonCallableMock(spec=[])
        factory = NonCallableMock(spec=[])
        listener = Mock(spec=["socket"])

        start_server(reactor, factory)
        dfr.callback(listener)

        executor.start.assert_called_once_with(reactor)
        _getUtility.assert_called_once_with(IHubServerConfig)
        with_port.assert_called_once_with(config.pbport)
        _serverFromString.assert_called_once_with(reactor, descriptor)
        server.listen.assert_called_once_with(factory)
        _setKeepAlive.assert_called_once_with(listener.socket)


class stop_server_test(TestCase):
    @patch("{src}._executors".format(**PATH), autospec=True)
    def test_stop_server(t, _executors):
        _executors.values.return_value = [Mock() for _ in range(3)]

        stop_server()

        for executor in _executors.values():
            executor.stop.assert_called_once_with()


class MakeServerFactoryTest(TestCase):
    """Test the make_server_factory function."""

    @patch("{src}.ZenPBServerFactory".format(**PATH), autospec=True)
    @patch("{src}.portal".format(**PATH), autospec=True)
    @patch("{src}.HubRealm".format(**PATH), autospec=True)
    @patch("{src}.HubAvatar".format(**PATH), autospec=True)
    def test_make_server_factory(
        self,
        _HubAvatar,
        _HubRealm,
        _portal,
        _ZenPBServerFactory,
    ):
        avatar = NonCallableMock()
        _HubAvatar.return_value = avatar
        realm = NonCallableMock()
        _HubRealm.return_value = realm
        hubportal = NonCallableMock()
        _portal.Portal.return_value = hubportal
        factory = NonCallableMock()
        _ZenPBServerFactory.return_value = factory

        pools = NonCallableMock()
        manager = NonCallableMock()
        authenticators = NonCallableMock()

        result = make_server_factory(pools, manager, authenticators)

        self.assertIs(factory, result)
        _HubAvatar.assert_called_once_with(manager, pools)
        _HubRealm.assert_called_once_with(avatar)
        _portal.Portal.assert_called_once_with(realm, authenticators)
        _ZenPBServerFactory.assert_called_once_with(hubportal)


class MakeServiceManagerTest(TestCase):
    """Test the make_service_manager function."""

    @patch("{src}.ServiceManager".format(**PATH), autospec=True)
    @patch("{src}.ServiceReferenceFactory".format(**PATH), autospec=True)
    @patch("{src}.ServiceLoader".format(**PATH), autospec=True)
    @patch("{src}.make_executors".format(**PATH), autospec=True)
    @patch("{src}.ServiceCallRouter".format(**PATH), autospec=True)
    @patch("{src}.ServiceRegistry".format(**PATH), autospec=True)
    @patch("{src}.getUtility".format(**PATH), autospec=True)
    def test_make_service_manager(
        self,
        _getUtility,
        _ServiceRegistry,
        _ServiceCallRouter,
        _make_executors,
        _ServiceLoader,
        _ServiceReferenceFactory,
        _ServiceManager,
    ):
        pools = NonCallableMock()
        config = _getUtility.return_value

        result = make_service_manager(pools)

        _getUtility.assert_called_once_with(IHubServerConfig)
        _ServiceRegistry.assert_called_once_with()
        _ServiceCallRouter.from_config.assert_called_once_with(config.routes)
        _make_executors.assert_called_once_with(config, pools)
        _ServiceLoader.assert_called_once_with()
        _ServiceReferenceFactory.assert_called_once_with(
            WorkerInterceptor,
            _ServiceCallRouter.from_config.return_value,
            _make_executors.return_value,
        )
        _ServiceManager.assert_called_once_with(
            _ServiceRegistry.return_value,
            _ServiceLoader.return_value,
            _ServiceReferenceFactory.return_value,
        )
        self.assertIs(result, _ServiceManager.return_value)


class MakePoolsTest(TestCase):
    """Test the make_pools function."""

    @patch("{src}.getUtility".format(**PATH), autospec=True)
    @patch("{src}.WorkerPool".format(**PATH), autospec=True)
    def test_make_pools(self, _WorkerPool, _getUtility):
        tests = (
            ["default"],
            ["foo", "bar"],
        )
        config_pools = _getUtility.return_value.pools
        for test in tests:
            config_pools.keys = lambda: test
            expected_values = [Mock() for _ in range(len(test))]
            _WorkerPool.side_effect = expected_values
            with subTest(pools=test):
                pools = make_pools()
                self.assertEqual(len(test), len(pools))
                self.assertSequenceEqual(sorted(test), sorted(pools.keys()))
                calls = [call(name) for name in test]
                _WorkerPool.assert_has_calls(calls)
                self.assertSequenceEqual(expected_values, pools.values())

            _WorkerPool.reset_mock()


class MakeExecutorsTest(TestCase):
    """Test the make_executors function."""

    @patch("{src}.import_name".format(**PATH), autospec=True)
    def test_make_executors(t, import_name):
        config = Mock(name="config")
        config.executors = {
            "executor_1": "module_path:class_name",
        }

        executor_1 = Mock(name="executor_1")
        import_name.return_value.create.return_value = executor_1

        pool_1 = Mock(name="pool_1")
        pools = {
            "executor_1": pool_1,
        }

        ret = make_executors(config, pools)

        import_name.assert_called_with("module_path", "class_name")
        import_name.return_value.create.assert_called_with(
            "executor_1", config=config, pool=pool_1
        )
        t.assertEqual(ret["executor_1"], executor_1)
