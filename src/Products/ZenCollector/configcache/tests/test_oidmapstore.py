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
import json
import time

from hashlib import md5
from unittest import TestCase

from Products.Jobber.tests.utils import subTest, RedisLayer

from ..cache import OidMapRecord, ConfigStatus
from ..cache.storage import OidMapStore


class EmptyOidMapStoreTest(TestCase):
    """Test an empty OidMapStore object."""

    layer = RedisLayer

    def setUp(t):
        t.store = OidMapStore(t.layer.redis)

    def tearDown(t):
        del t.store

    def test_nonzero(t):
        t.assertFalse(t.store)

    def test_remove(t):
        t.assertIsNone(t.store.remove())

    def test_get_created(t):
        t.assertIsNone(t.store.get_created())

    def test_get_checksum(t):
        t.assertIsNone(t.store.get_checksum())

    def test_get_status(t):
        result = t.store.get_status()
        t.assertIsNone(result)

    def test_get_with_default_default(t):
        t.assertIsNone(t.store.get())

    def test_get_with_nondefault_default(t):
        dflt = object()
        t.assertEqual(t.store.get(dflt), dflt)


class OidMapStoreTest(TestCase):

    layer = RedisLayer

    def setUp(t):
        t.store = OidMapStore(t.layer.redis)
        t.created = time.time()
        t.oidmap = {"1.1.1": "foo"}
        t.checksum = md5(  # noqa: S324
            json.dumps(t.oidmap, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def tearDown(t):
        del t.store

    def test_add(t):
        record = OidMapRecord(t.created, t.checksum, t.oidmap)
        t.store.add(record)

        actual_record = t.store.get()
        t.assertEqual(record, actual_record)
        t.assertEqual(t.created, t.store.get_created())
        t.assertEqual(t.checksum, t.store.get_checksum())
        t.assertTrue(t.store)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(status.updated, t.created)

    def test_add_with_prior_status(t):
        now = time.time()
        t.store.set_pending(now)

        record = OidMapRecord(t.created, t.checksum, t.oidmap)
        t.store.add(record)

        actual_record = t.store.get()
        t.assertEqual(record, actual_record)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(status.updated, t.created)

    def test_put_when_empty(t):
        record = OidMapRecord(t.created, t.checksum, t.oidmap)
        t.store.put(record)

        actual_record = t.store.get()
        t.assertEqual(record, actual_record)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Current)
        t.assertEqual(status.updated, t.created)

    def test_put_with_prior_status(t):
        now = time.time()
        t.store.set_pending(now)

        record = OidMapRecord(t.created, t.checksum, t.oidmap)
        t.store.put(record)

        actual_record = t.store.get()
        t.assertEqual(record, actual_record)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(status.submitted, now)

    def test_set_expired(t):
        now = time.time()
        t.store.set_expired(now)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Expired)
        t.assertEqual(status.expired, now)

    def test_set_pending(t):
        now = time.time()
        t.store.set_pending(now)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Pending)
        t.assertEqual(status.submitted, now)

    def test_set_building(t):
        now = time.time()
        t.store.set_building(now)

        status = t.store.get_status()
        t.assertIsInstance(status, ConfigStatus.Building)
        t.assertEqual(status.started, now)

    def test_remove(t):
        record = OidMapRecord(t.created, t.checksum, t.oidmap)
        t.store.add(record)
        t.store.remove()

        t.assertIsNone(t.store.get())
        t.assertIsNone(t.store.get_status())
        t.assertIsNone(t.store.get_checksum())
        t.assertIsNone(t.store.get_created())
        t.assertFalse(t.store)
