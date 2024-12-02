##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from mock import patch
from Products.ZenUtils.Utils import is_browser_connection_open, zhttp_channel

PATH = {'src': 'Products.ZenUtils.Utils'}


class TestIsBrowserConnectionOpen(unittest.TestCase):

    def setUp(t):
        t.request = type("request", (object,), {})()

    def test_missing_environ(t):
        result = is_browser_connection_open(t.request)
        t.assertFalse(result)

    def test_missing_env_creation_time(t):
        t.request.environ = {}
        result = is_browser_connection_open(t.request)
        t.assertFalse(result)

    @patch("{src}.asyncore".format(**PATH), autospec=True)
    def test_no_channels(t, _asyncore):
        t.request.environ = {"channel.creation_time": 10}
        _asyncore.socket_map = {"foo": object()}
        result = is_browser_connection_open(t.request)
        t.assertFalse(result)

    @patch("{src}.asyncore".format(**PATH), autospec=True)
    def test_no_creation_time_on_channel(t, _asyncore):
        t.request.environ = {"channel.creation_time": 10}
        _asyncore.socket_map = {"foo": _FakeChannel()}
        result = is_browser_connection_open(t.request)
        t.assertFalse(result)

    @patch("{src}.asyncore".format(**PATH), autospec=True)
    def test_mismatch_creation_time(t, _asyncore):
        t.request.environ = {"channel.creation_time": 10}
        _asyncore.socket_map = {"foo": _FakeChannel(creation_time=20)}
        result = is_browser_connection_open(t.request)
        t.assertFalse(result)

    @patch("{src}.asyncore".format(**PATH), autospec=True)
    def test_matching_creation_time(t, _asyncore):
        t.request.environ = {"channel.creation_time": 10}
        _asyncore.socket_map = {"foo": _FakeChannel(creation_time=10)}
        result = is_browser_connection_open(t.request)
        t.assertTrue(result)


class _FakeChannel(zhttp_channel):

    def __init__(self, **kw):
        self.socket = type("socket", (object,), kw)
