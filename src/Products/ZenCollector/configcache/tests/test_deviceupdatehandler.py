
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

from unittest import TestCase

from mock import Mock, patch

from ..cache import DeviceKey, ConfigStatus
from ..cache.storage import DeviceConfigStore
from ..dispatcher import DeviceConfigTaskDispatcher
from ..handlers import DeviceUpdateHandler


PATH = {"src": "Products.ZenCollector.configcache.handlers"}


class DeviceUpdateHandlerTest(TestCase):
    """Test the DeviceUpdateHandler object."""

    def setUp(t):
        t.store = Mock(DeviceConfigStore)
        t.dispatcher = Mock(DeviceConfigTaskDispatcher)
        t.dispatcher.service_names = ("ServiceA", "ServiceB")
        t.log = Mock(logging.getLogger("zen"))
        t.handler = DeviceUpdateHandler(t.log, t.store, t.dispatcher)

    def tearDown(t):
        del t.handler
        del t.log
        del t.dispatcher
        del t.store

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_current_to_expired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        updated1 = 33330.0
        updated2 = 33331.0
        now = 34000.0
        _time.time.return_value = now

        status1 = ConfigStatus.Current(key1, updated1)
        status2 = ConfigStatus.Current(key2, updated2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 100.0)

        t.store.set_retired.assert_called_with()
        t.store.set_expired.assert_called_with((key2, now), (key1, now))

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_current_to_retired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        updated1 = 33330.0
        updated2 = 33331.0
        now = 34000.0
        _time.time.return_value = now

        status1 = ConfigStatus.Current(key1, updated1)
        status2 = ConfigStatus.Current(key2, updated2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 1000.0)

        t.store.set_retired.assert_called_with((key2, now), (key1, now))
        t.store.set_expired.assert_called_with()

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_current_to_retired_and_expired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'd', 'c2')
        updated1 = 33330.0
        updated2 = 32331.0
        now = 34000.0
        _time.time.return_value = now

        status1 = ConfigStatus.Current(key1, updated1)
        status2 = ConfigStatus.Current(key2, updated2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 1000.0)

        t.store.set_retired.assert_called_with((key1, now))
        t.store.set_expired.assert_called_with((key2, now))

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_pending_to_expired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        updated1 = 33330.0
        updated2 = 32331.0
        now = 34000.0
        _time.time.return_value = now

        status1 = ConfigStatus.Pending(key1, updated1)
        status2 = ConfigStatus.Pending(key2, updated2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 1000.0)

        t.store.set_retired.assert_called_with()
        t.store.set_expired.assert_called_with((key2, now), (key1, now))

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_only_expired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        expired1 = 33330.0
        expired2 = 33331.0
        _time.time.return_value = 34000.0

        status1 = ConfigStatus.Expired(key1, expired1)
        status2 = ConfigStatus.Expired(key2, expired2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 100.0)

        t.store.set_retired.assert_called_with()
        t.store.set_expired.assert_called_with()

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_only_retired(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        expired1 = 33330.0
        expired2 = 33331.0
        _time.time.return_value = 34000.0

        status1 = ConfigStatus.Retired(key1, expired1)
        status2 = ConfigStatus.Retired(key2, expired2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 1000.0)

        t.store.set_retired.assert_called_with()
        t.store.set_expired.assert_called_with()

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_only_building(t, _time):
        key1 = DeviceKey('a', 'b', 'c1')
        key2 = DeviceKey('a', 'b', 'c2')
        expired1 = 33330.0
        expired2 = 33331.0
        _time.time.return_value = 34000.0
        now = 34000.0

        status1 = ConfigStatus.Building(key1, expired1)
        status2 = ConfigStatus.Building(key2, expired2)
        t.store.get_status.side_effect = (status1, status2)

        t.handler((key1, key2), 1000.0)

        t.store.set_retired.assert_called_with()
        t.store.set_expired.assert_called_with((key2, now), (key1, now))
