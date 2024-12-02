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

from Products.ZenUtils.MySqlZodbFactory import (
    MySQLdb,
    _get_storage,
    _OPERATIONAL_ERROR_RETRY_DELAY,
)

PATH = {"src": "Products.ZenUtils.MySqlZodbFactory"}


class TestGetStorage(TestCase):
    """Test the _get_storage function."""

    def setUp(t):
        log = logging.getLogger()
        log.setLevel(logging.FATAL + 1)

    def tearDown(t):
        log = logging.getLogger()
        log.setLevel(logging.NOTSET)

    @patch("{src}.relstorage.storage.RelStorage".format(**PATH), autospec=True)
    def test_nominal(t, relstorage_):
        params = {"a": 1}
        adapter = Mock()

        storage = _get_storage(adapter, params)

        t.assertEqual(storage, relstorage_.return_value)
        relstorage_.assert_called_with(adapter, a=1)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.relstorage.storage.RelStorage".format(**PATH), autospec=True)
    def test_operational_error(t, relstorage_, time_):
        params = {"a": 1}
        adapter = Mock()

        ex = MySQLdb.OperationalError()
        relstorage_.side_effect = ex

        sleep_calls = (
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
            call(_OPERATIONAL_ERROR_RETRY_DELAY),
        )

        storage = _get_storage(adapter, params)

        t.assertIsNone(storage)
        time_.sleep.assert_has_calls(sleep_calls)
        t.assertEqual(len(sleep_calls), relstorage_.call_count)
        t.assertEqual(len(sleep_calls), time_.sleep.call_count)

    @patch("{src}.time".format(**PATH), autospec=True)
    @patch("{src}.relstorage.storage.RelStorage".format(**PATH), autospec=True)
    def test_unexpected_error(t, relstorage_, time_):
        params = {"a": 1}
        adapter = Mock()

        ex = Exception()
        relstorage_.side_effect = ex

        storage = _get_storage(adapter, params)

        t.assertIsNone(storage)
        t.assertEqual(1, relstorage_.call_count)
        t.assertEqual(0, time_.call_count)
