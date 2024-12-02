##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import collections

from unittest import TestCase

from mock import patch

from Products.ZenCollector.services.config import DeviceProxy
from Products.Jobber.tests.utils import RedisLayer

from ...cache import DeviceKey, DeviceRecord, ConfigStatus
from ...cache.storage import DeviceConfigStore
from ..list import ListDevice


_fields = collections.namedtuple(
    "_fields", "service monitor device uid updated"
)

PATH = {"src": "Products.ZenCollector.configcache.cli.list"}

_Args = collections.namedtuple(
    "_Args", "service collector show_uid device states"
)


class _BaseTest(TestCase):
    # Base class to share setup code

    layer = RedisLayer

    fields = (
        _fields("svc1", "mon1", "abc-01", "/abc-01", 1234500.0),
        _fields("svc1", "mon1", "abc-02", "/abc-02", 1234550.0),
        _fields("svc2", "mon1", "efg-01", "/efg-01", 1234550.0),
    )

    def setUp(t):
        DeviceProxy.__eq__ = _compare_configs
        t.store = DeviceConfigStore(t.layer.redis)
        t.config1 = _make_config("abc-01", "_abc_01", "abef394c")
        t.config2 = _make_config("abc-02", "_abc_02", "fbd987ba")
        t.config3 = _make_config("efg-01", "_efg_01", "39da34cf")
        t.record1 = DeviceRecord.make(
            t.fields[0].service,
            t.fields[0].monitor,
            t.fields[0].device,
            t.fields[0].uid,
            t.fields[0].updated,
            t.config1,
        )
        t.record2 = DeviceRecord.make(
            t.fields[1].service,
            t.fields[1].monitor,
            t.fields[1].device,
            t.fields[1].uid,
            t.fields[1].updated,
            t.config2,
        )
        t.record3 = DeviceRecord.make(
            t.fields[2].service,
            t.fields[2].monitor,
            t.fields[2].device,
            t.fields[2].uid,
            t.fields[2].updated,
            t.config3,
        )
        t.store.add(t.record1)
        t.store.add(t.record2)
        t.store.add(t.record3)

    def tearDown(t):
        del t.store
        del t.config1
        del t.config2
        del t.config3
        del t.record1
        del t.record2
        del t.record3
        del DeviceProxy.__eq__


class ListDeviceTest(_BaseTest):
    """Test the ListDevice class."""

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_no_args(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "*", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(3, len(statuses))
        statuses = sorted(statuses, key=lambda s: s.key)
        t.assertTrue(
            all(isinstance(st, ConfigStatus.Current) for st in statuses)
        )
        for n in range(3):
            key = DeviceKey(
                t.fields[n].service,
                t.fields[n].monitor,
                t.fields[n].device,
            )
            t.assertEqual(statuses[n].key, key)
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_matched_device(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "*", False, ["abc*"], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(True)
        t.assertEqual(2, len(statuses))
        statuses = sorted(statuses, key=lambda s: s.key)
        t.assertTrue(
            all(isinstance(st, ConfigStatus.Current) for st in statuses)
        )
        for n in range(2):
            key = DeviceKey(
                t.fields[n].service,
                t.fields[n].monitor,
                t.fields[n].device,
            )
            t.assertEqual(statuses[n].key, key)
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_multiple_devices(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "*", False, ["abc-01", "abc-02"], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(2, len(statuses))
        statuses = sorted(statuses, key=lambda s: s.key)
        for n in range(2):
            expectedkey = DeviceKey(
                t.fields[n].service,
                t.fields[n].monitor,
                t.fields[n].device,
            )
            t.assertEqual(statuses[n].key, expectedkey)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_unmatched_device(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "*", False, ["abc"], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(0, len(statuses))
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_matched_service(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*1", "*", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(2, len(statuses))
        statuses = sorted(statuses, key=lambda s: s.key)
        for n in range(2):
            key = DeviceKey(
                t.fields[n].service,
                t.fields[n].monitor,
                t.fields[n].device,
            )
            t.assertEqual(statuses[n].key, key)
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_unmatched_service(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("svc", "*", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(0, len(statuses))
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_matched_monitor(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "*1", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(3, len(statuses))
        statuses = sorted(statuses, key=lambda s: s.key)
        for n in range(3):
            key = DeviceKey(
                t.fields[n].service,
                t.fields[n].monitor,
                t.fields[n].device,
            )
            t.assertEqual(statuses[n].key, key)
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_unmatched_monitor(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "mon", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(0, len(statuses))
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_nonoverlapping_service(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("svc2", "*", False, ["abc-01", "abc-02"], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(0, len(statuses))
        t.assertDictEqual({}, oidmap)

    @patch("{src}.createObject".format(**PATH), autospec=True)
    @patch("{src}.getRedisClient".format(**PATH), autospec=True)
    def test_nonoverlapping_monitor(t, _getRedisClient, _createObject):
        _getRedisClient.return_value = t.layer.redis
        _createObject.return_value = t.store
        args = _Args("*", "mon2", False, [], [])
        cmd = ListDevice(args)

        statuses, oidmap = cmd._get(False)
        t.assertEqual(0, len(statuses))
        t.assertDictEqual({}, oidmap)


def _make_config(_id, configId, guid):
    config = DeviceProxy()
    config.id = _id
    config._config_id = configId
    config._device_guid = guid
    config.data = "fancy"
    return config


def _compare_configs(self, cfg):
    # _compare_configs used to monkeypatch DeviceProxy
    # to make equivalent instances equal.
    return all(
        (
            self.id == cfg.id,
            self._config_id == cfg._config_id,
            self._device_guid == cfg._device_guid,
        )
    )
