##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from unittest import TestCase

from mock import call, Mock, patch

from Products.Jobber.worker import (
    MySQLdb,
    setup_zodb,
    _OPERATIONAL_ERROR_RETRY_DELAY,
)

PATH = {"src": "Products.Jobber.worker"}


class TestSetupZODB(TestCase):
    """Test the setup_zodb function."""

    def setUp(t):
        log = logging.getLogger()
        log.setLevel(logging.FATAL + 1)

    def tearDown(t):
        log = logging.getLogger()
        log.setLevel(logging.NOTSET)

    @patch("{src}.ZODB".format(**PATH), autospec=True)
    @patch("{src}.get_app".format(**PATH), autospec=True)
    @patch("{src}.getConfig".format(**PATH), autospec=True)
    def test_nominal(t, getConfig_, get_app_, zodb_):
        db = Mock()
        app = Mock()
        filename = "config/zodb.conf"
        config = {"zodb-config-file": filename}
        zodb_.config.databaseFromURL.return_value = db
        get_app_.return_value = app
        getConfig_.return_value = config

        setup_zodb()

        t.assertTrue(hasattr(app, "db"))
        t.assertEqual(app.db, db)
        zodb_.config.databaseFromURL.assert_called_with("file://" + filename)

    @patch("{src}.ZODB".format(**PATH), autospec=True)
    @patch("{src}.get_app".format(**PATH), autospec=True)
    @patch("{src}.getConfig".format(**PATH), autospec=True)
    @patch("{src}.time".format(**PATH), autospec=True)
    def test_operational_error(t, time_, getConfig_, get_app_, zodb_):
        timeout = 100
        appconfig = {"worker_proc_alive_timeout": timeout}
        app = Mock()
        app.conf = appconfig
        get_app_.return_value = app

        ex = MySQLdb.OperationalError()
        zodb_.config.databaseFromURL.side_effect = ex

        filename = "config/zodb.conf"
        config = {"zodb-config-file": filename}
        getConfig_.return_value = config

        sleep_calls = (
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
        )

        with t.assertRaises(SystemExit):
            setup_zodb()

        time_.sleep.assert_has_calls(sleep_calls)
        t.assertEqual(
            len(sleep_calls), zodb_.config.databaseFromURL.call_count
        )
        t.assertEqual(len(sleep_calls), time_.sleep.call_count)

    @patch("{src}.ZODB".format(**PATH), autospec=True)
    @patch("{src}.get_app".format(**PATH), autospec=True)
    @patch("{src}.getConfig".format(**PATH), autospec=True)
    @patch("{src}.time".format(**PATH), autospec=True)
    def test_unexpected_error(t, time_, getConfig_, get_app_, zodb_):
        timeout = 100
        appconfig = {"worker_proc_alive_timeout": timeout}
        app = Mock()
        app.conf = appconfig
        get_app_.return_value = app

        ex = Exception()
        zodb_.config.databaseFromURL.side_effect = ex

        filename = "config/zodb.conf"
        config = {"zodb-config-file": filename}
        getConfig_.return_value = config

        with t.assertRaises(SystemExit):
            setup_zodb()

        t.assertEqual(1, zodb_.config.databaseFromURL.call_count)
