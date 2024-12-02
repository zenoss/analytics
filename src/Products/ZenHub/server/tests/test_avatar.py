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
from mock import create_autospec, MagicMock, patch, sentinel

from ..avatar import HubAvatar, RemoteBadMonitor, pb
from ..service import ServiceManager
from ..workerpool import WorkerPool

PATH = {"src": "Products.ZenHub.server.avatar"}


class HubAvatarTest(TestCase):
    """Test the HubAvatar class."""

    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH), autospec=True
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.services = create_autospec(ServiceManager)
        t.pools = {
            "foo": WorkerPool("foo"),
            "bar": WorkerPool("bar"),
        }
        t.avatar = HubAvatar(t.services, t.pools)

    def test_perspective_ping(t):
        ret = t.avatar.perspective_ping()
        t.assertEqual(ret, "pong")

    @patch("{src}.os".format(**PATH), name="os", autospec=True)
    def test_perspective_getHubInstanceId_normal(t, _os):
        key = "CONTROLPLANE_INSTANCE_ID"
        hubId = "hub"

        def side_effect(k, d):
            if k == key:
                return hubId
            return d

        _os.environ.get.side_effect = side_effect

        actual = t.avatar.perspective_getHubInstanceId()

        t.assertEqual(actual, hubId)

    @patch("{src}.os".format(**PATH), name="os", autospec=True)
    def test_perspective_getHubInstanceId_unknown(t, _os):
        _os.environ.get.side_effect = lambda k, d: d
        actual = t.avatar.perspective_getHubInstanceId()
        t.assertEqual(actual, "Unknown")

    def test_perspective_getService_no_listener(t):
        service_name = "testservice"
        monitor = "localhost"

        expected = t.services.getService.return_value
        actual = t.avatar.perspective_getService(service_name, monitor)

        t.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_not_called()
        t.assertEqual(expected, actual)

    def test_perspective_getService_with_listener(t):
        service_name = "testservice"
        monitor = "localhost"
        listener = sentinel.listener
        options = sentinel.options

        expected = t.services.getService.return_value
        actual = t.avatar.perspective_getService(
            service_name,
            monitor,
            listener=listener,
            options=options,
        )

        t.services.getService.assert_called_with(service_name, monitor)
        expected.addListener.assert_called_once_with(listener, options)
        t.assertEqual(expected, actual)

    def test_perspective_getService_raises_RemoteBadMonitor(t):
        t.services.getService.side_effect = RemoteBadMonitor("tb", "msg")
        with t.assertRaises(RemoteBadMonitor):
            t.avatar.perspective_getService("service_name")

    @patch("{src}.getLogger".format(**PATH))
    def test_perspective_getService_raises_error(t, getLogger):
        logger = getLogger.return_value
        t.avatar._HubAvatar__log = logger
        service_name = "service_name"
        t.services.getService.side_effect = Exception()

        with t.assertRaises(pb.Error):
            t.avatar.perspective_getService(service_name)
            logger.exception.assert_called_once_with(
                "Failed to get service '%s'",
                service_name,
            )

    def test_perspective_reportForWork_nominal(t):
        remote = MagicMock(pb.RemoteReference, autospec=True)
        pool_name = "foo"
        name = "default_0"

        disconnect_callback = []

        def _notifyOnDisconnect(callback):
            disconnect_callback.append(callback)

        remote.notifyOnDisconnect.side_effect = _notifyOnDisconnect

        # Add the worker
        t.avatar.perspective_reportForWork(remote, name, pool_name)

        foo = t.pools[pool_name]
        worker = foo.get(name)
        t.assertIsNotNone(worker)
        t.assertEqual(worker.remote, remote)

        # Remove the worker
        t.assertEqual(
            1,
            len(disconnect_callback),
            "notifyOnDisconnect not called",
        )
        disconnect_callback[0](remote)
        worker = foo.get(name)
        t.assertIsNone(worker)

    def test_perspective_resignFromWork_nominal(t):
        remote = MagicMock(pb.RemoteReference, autospec=True)
        name = "default-1"
        worklist = "foo"
        pool = t.pools[worklist]

        # Add the worker
        t.avatar.perspective_reportForWork(remote, name, worklist)
        worker = pool.get(name)
        t.assertIsNotNone(worker)

        # Resign the worker
        t.avatar.perspective_resignFromWork(name, worklist)
        worker = pool.get(name)
        t.assertIsNone(worker)
