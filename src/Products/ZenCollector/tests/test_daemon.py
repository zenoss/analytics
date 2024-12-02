from mock import ANY, Mock, patch, create_autospec
from unittest import TestCase

from Products.ZenHub.tests.mock_interface import create_interface_mock

from Products.ZenCollector.daemon import (
    CollectorDaemon,
    defer,
    ICollectorPreferences,
    IConfigurationListener,
    ITaskSplitter,
)


class TestCollectorDaemon_maintenanceCallback(TestCase):
    def setUp(t):
        # Patch out the  __init__ method, due to excessive side-effects
        t.init_patcher = patch.object(
            CollectorDaemon, "__init__", autospec=True, return_value=None
        )
        t.init_patcher.start()
        t.addCleanup(t.init_patcher.stop)

        preferences = create_interface_mock(ICollectorPreferences)()
        taskSplitter = create_interface_mock(ITaskSplitter)()
        configurationListener = create_interface_mock(IConfigurationListener)()

        t.cd = CollectorDaemon(
            preferences, taskSplitter, configurationListener
        )
        t.cd.log = Mock(name="log")
        t.cd._prefs = Mock(
            name="options",
            spec_set=["pauseUnreachableDevices"],
            pauseUnreachableDevices=True,
        )
        t.cd.options = Mock(name="options", spec_set=["cycle"], cycle=True)
        t.cd.getDevicePingIssues = create_autospec(t.cd.getDevicePingIssues)
        t.cd._unresponsiveDevices = set()

    def test__maintenanceCallback(t):
        ret = t.cd._maintenanceCallback()

        t.cd.log.debug.assert_called_with(
            "deviceIssues=%r", t.cd.getDevicePingIssues.return_value
        )
        t.assertIsNone(ret.result)

    def test_ignores_unresponsive_devices(t):
        t.cd.log = Mock(name="log")
        t.cd._prefs.pauseUnreachableDevices = False

        ret = t.cd._maintenanceCallback()

        t.assertEqual(ret.result, None)

    def test_no_cycle_option(t):
        t.cd.log = Mock(name="log")
        t.cd._prefs.pauseUnreachableDevices = False
        t.cd.options.cycle = False

        ret = t.cd._maintenanceCallback()

        t.assertIsNone(ret.result)

    def test_handle_getDevicePingIssues_exception(t):
        t.cd.getDevicePingIssues.side_effect = Exception

        handler = _Capture()
        ret = t.cd._maintenanceCallback()
        ret.addErrback(handler)

        t.assertIsNone(handler.err)
        t.cd.log.exception.assert_called_once_with(ANY)

    def test_handle__pauseUnreachableDevices_exception(t):
        t.cd._pauseUnreachableDevices = create_autospec(
            t.cd._pauseUnreachableDevices
        )
        t.cd._pauseUnreachableDevices.side_effect = Exception

        handler = _Capture()
        ret = t.cd._maintenanceCallback()
        ret.addErrback(handler)

        t.assertIsNone(handler.err)
        t.cd.log.exception.assert_called_once_with(ANY)

    def test__pauseUnreachableDevices(t):
        t.cd._scheduler = Mock(
            name="_scheduler",
            spec_set=["resumeTasksForConfig", "pauseTasksForConfig"],
        )
        t.cd._unresponsiveDevices = {"d1", "d2"}
        issues = tuple((d, "count", "total") for d in ["d2", "d3"])
        t.cd.getDevicePingIssues.return_value = issues

        ret = t.cd._pauseUnreachableDevices()

        t.cd._scheduler.resumeTasksForConfig.assert_called_with("d1")
        t.cd._scheduler.pauseTasksForConfig.assert_called_with("d3")
        t.assertIsInstance(ret, defer.Deferred)
        t.assertEqual(ret.result, issues)


class _Capture(object):
    def __init__(self):
        self.err = None

    def __call__(self, result):
        self.err = result
