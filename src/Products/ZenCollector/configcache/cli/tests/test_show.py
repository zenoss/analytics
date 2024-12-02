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

from Products.ZenCollector.services.config import DeviceProxy
from Products.Jobber.tests.utils import RedisLayer

from ...cache import DeviceRecord
from ...cache.storage import DeviceConfigStore
from ..show import _query_cache


_fields = collections.namedtuple(
    "_fields", "service monitor device uid updated"
)

PATH = {"src": "Products.ZenCollector.configcache.cli.list"}


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


class QueryCacheTest(_BaseTest):
    """Test the _query_cache function."""

    def test_unmatched_service(t):
        svc, mon, dvc = ("1", "mon1", "abc-01")

        results, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNone(results)
        t.assertIsNotNone(err)

    def test_unmatched_monitor(t):
        svc, mon, dvc = ("svc1", "1", "abc-01")

        results, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNone(results)
        t.assertIsNotNone(err)

    def test_unmatched_device(t):
        svc, mon, dvc = ("svc1", "mon1", "abc")

        results, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNone(results)
        t.assertIsNotNone(err)

    def test_multiple_devices(t):
        svc, mon, dvc = ("svc1", "mon1", "abc*")

        results, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNone(results)
        t.assertIsNotNone(err)

    def test_matching_service(t):
        svc, mon, dvc = ("*1", "mon1", "abc-01")

        record, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNotNone(record)
        t.assertIsNone(err)

    def test_matching_monitor(t):
        svc, mon, dvc = ("svc1", "*1", "abc-01")

        record, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNotNone(record)
        t.assertIsNone(err)

    def test_matching_device(t):
        svc, mon, dvc = ("svc1", "mon1", "a*1")

        record, err = _query_cache(t.store, svc, mon, dvc)
        t.assertIsNotNone(record)
        t.assertIsNone(err)


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
