##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from cStringIO import StringIO

from mock import MagicMock, Mock, patch, sentinel, call
from unittest import TestCase

from ..log import (
    apply_levels,
    configure_logging,
    load_log_level_config,
    _loglevel_confs,
)
from .utils import LoggingLayer

UNEXPECTED = type("UNEXPECTED", (object,), {})()
PATH = {"src": "Products.Jobber.log"}


class ConfigureLoggingTest(TestCase):
    """Test the configure_logging function."""

    @patch("{src}.os".format(**PATH), autospec=True)
    @patch("{src}.sys".format(**PATH), autospec=True)
    @patch("{src}.logging".format(**PATH), autospec=True)
    @patch("{src}._get_logger".format(**PATH), autospec=True)
    @patch("{src}.FormatStringAdapter".format(**PATH), autospec=True)
    @patch("{src}.LoggingProxy".format(**PATH), autospec=True)
    @patch("{src}.apply_levels".format(**PATH), autospec=True)
    @patch("{src}.load_log_level_config".format(**PATH), autospec=True)
    def test_nominal(
        t,
        _load_log_level_config,
        _apply_levels,
        _LoggingProxy,
        _FormatStringAdapter,
        _get_logger,
        _logging,
        _sys,
        _os,
    ):
        exists = _os.path.exists
        getLogger = _logging.getLogger
        levelConfig = _load_log_level_config.return_value
        logs = {
            "STDOUT": sentinel.stdout_log,
            "STDERR": sentinel.stderr_log,
        }
        getLogger.side_effect = lambda n: logs[n]
        getLogger_calls = [call("STDOUT"), call("STDERR")]
        proxies = {
            logs["STDOUT"]: sentinel.stdout_proxy,
            logs["STDERR"]: sentinel.stderr_proxy,
        }
        out_proxy = proxies[logs["STDOUT"]]
        err_proxy = proxies[logs["STDERR"]]
        _LoggingProxy.side_effect = lambda x: proxies[x]
        proxy_calls = [
            call(logs["STDOUT"]),
            call(logs["STDERR"]),
        ]

        exists.return_value = True

        configure_logging("zenjobs")

        loglevel_confname = _loglevel_confs["zenjobs"]
        exists.assert_called_once_with(loglevel_confname)
        _load_log_level_config.assert_called_once_with(loglevel_confname)
        _apply_levels.assert_called_once_with(levelConfig)

        getLogger.assert_has_calls(getLogger_calls, any_order=True)
        _LoggingProxy.assert_has_calls(proxy_calls, any_order=True)

        t.assertEqual(_sys.__stdout__, out_proxy)
        t.assertEqual(_sys.stdout, out_proxy)
        t.assertEqual(_sys.__stderr__, err_proxy)
        t.assertEqual(_sys.stderr, err_proxy)

    @patch("{src}.os".format(**PATH), autospec=True)
    @patch("{src}.sys".format(**PATH), autospec=True)
    @patch("{src}.logging".format(**PATH), autospec=True)
    @patch("{src}._get_logger".format(**PATH), autospec=True)
    @patch("{src}.FormatStringAdapter".format(**PATH), autospec=True)
    @patch("{src}.LoggingProxy".format(**PATH), autospec=True)
    @patch("{src}.apply_levels".format(**PATH), autospec=True)
    @patch("{src}.load_log_level_config".format(**PATH), autospec=True)
    def test_missing_loglevel_file(
        t,
        _load_log_level_config,
        _apply_levels,
        _LoggingProxy,
        _FormatStringAdapter,
        _get_logger,
        _logging,
        _sys,
        _os,
    ):
        exists = _os.path.exists
        getLogger = _logging.getLogger
        logs = {
            "STDOUT": sentinel.stdout_log,
            "STDERR": sentinel.stderr_log,
        }
        getLogger.side_effect = lambda n: logs[n]
        getLogger_calls = [call("STDOUT"), call("STDERR")]
        proxies = {
            logs["STDOUT"]: sentinel.stdout_proxy,
            logs["STDERR"]: sentinel.stderr_proxy,
        }
        out_proxy = proxies[logs["STDOUT"]]
        err_proxy = proxies[logs["STDERR"]]
        _LoggingProxy.side_effect = lambda x: proxies[x]
        proxy_calls = [
            call(logs["STDOUT"]),
            call(logs["STDERR"]),
        ]

        exists.return_value = False

        configure_logging("zenjobs")

        exists.assert_called_once_with(_loglevel_confs["zenjobs"])
        _load_log_level_config.assert_has_calls([])
        _apply_levels.assert_has_calls([])

        getLogger.assert_has_calls(getLogger_calls, any_order=True)
        _LoggingProxy.assert_has_calls(proxy_calls, any_order=True)

        t.assertEqual(_sys.__stdout__, out_proxy)
        t.assertEqual(_sys.stdout, out_proxy)
        t.assertEqual(_sys.__stderr__, err_proxy)
        t.assertEqual(_sys.stderr, err_proxy)


class LoadLogLevelConfigTest(TestCase):
    """Test the load_log_level_config function."""

    @patch("{src}.open".format(**PATH))
    def test_nominal(t, _open):
        data = StringIO("foo.bar INFO\nfoo.baz WARNING\n")
        ctxm = MagicMock()
        ctxm.__enter__ = Mock(return_value=data)
        ctxm.__exit__ = Mock(return_value=False)
        _open.return_value = ctxm
        filename = "foo_levels.conf"
        expected = {"foo.bar": "INFO", "foo.baz": "WARNING"}

        actual = load_log_level_config(filename)

        t.assertDictEqual(expected, actual)

    @patch("{src}.open".format(**PATH))
    def test_extra_columns(t, _open):
        data = StringIO("foo.bar INFO\nfoo.baz WARNING # temporary\n")
        ctxm = MagicMock()
        ctxm.__enter__ = Mock(return_value=data)
        ctxm.__exit__ = Mock(return_value=False)
        _open.return_value = ctxm
        filename = "foo_levels.conf"
        expected = {"foo.bar": "INFO", "foo.baz": "WARNING"}

        actual = load_log_level_config(filename)

        t.assertDictEqual(expected, actual)


class ApplyLevelsTest(TestCase):
    """Test the apply_levels function."""

    layer = LoggingLayer

    def setUp(t):
        t.layer.manager.loggerDict.clear()

    def test_empty(t):
        apply_levels({})
        t.assertDictEqual({}, logging.root.manager.loggerDict)

    def test_nominal(t):
        config = {
            "zen": "INFO",
            "zen.foo.bar": "DEBUG",
        }
        apply_levels(config)
        t.assertIn("zen", logging.root.manager.loggerDict)
        t.assertIn("zen.foo.bar", logging.root.manager.loggerDict)
        t.assertEqual(logging.INFO, logging.getLogger("zen").level)
        t.assertEqual(logging.DEBUG, logging.getLogger("zen.foo.bar").level)
        t.assertEqual(logging.NOTSET, logging.getLogger("zen.foo").level)

    def test_other(t):
        config = {
            "boomboom": "ERROR",
        }
        apply_levels(config)
        t.assertIn("boomboom", logging.root.manager.loggerDict)
        t.assertEqual(logging.ERROR, logging.getLogger("boomboom").level)
