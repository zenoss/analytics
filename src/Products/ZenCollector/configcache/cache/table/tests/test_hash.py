##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from Products.Jobber.tests.utils import RedisLayer  # , subTest

from ..hash import Hash


class TestHashTable(TestCase):
    """Test the Hash table class."""

    layer = RedisLayer

    def setUp(t):
        t.key = "foo:bar"
        t.table = Hash()

    def tearDown(t):
        del t.table

    def test_no_data(t):
        field = "f1"
        t.assertFalse(t.table.exists(t.layer.redis, t.key))
        t.assertFalse(t.table.exists(t.layer.redis, t.key, field))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertIsNone(t.table.get(t.layer.redis, t.key))
        t.assertIsNone(t.table.getfield(t.layer.redis, t.key, field))
        t.assertIsNone(t.table.delete(t.layer.redis, t.key))

    def test_add_data(t):
        mapping = {"f1": "cookie", "f2": 2343.2}

        expected_get = {"f1": "cookie", "f2": "2343.2"}
        expected_scan = (t.key,)

        t.table.set(t.layer.redis, t.key, mapping)

        scan = tuple(t.table.scan(t.layer.redis, t.key))
        get = t.table.get(t.layer.redis, t.key)
        f1 = t.table.getfield(t.layer.redis, t.key, "f1")

        t.assertTrue(t.table.exists(t.layer.redis, t.key))
        t.assertTrue(t.table.exists(t.layer.redis, t.key, "f1"))
        t.assertTrue(t.table.exists(t.layer.redis, t.key, "f2"))
        t.assertTupleEqual(expected_scan, scan)
        t.assertDictEqual(expected_get, get)
        t.assertEqual(mapping["f1"], f1)

    def test_add_more_data(t):
        mapping = {"f1": "cookie", "f2": 2343.2}
        t.table.set(t.layer.redis, t.key, mapping)

        updated = {"f2": 1234.87, "f3": "baz"}
        t.table.set(t.layer.redis, t.key, updated)

        expected_get = {"f1": "cookie", "f2": "1234.87", "f3": "baz"}

        get = t.table.get(t.layer.redis, t.key)

        t.assertDictEqual(expected_get, get)

    def test_getfield(t):
        mapping = {"f1": "cookie", "f2": 2343.2}
        t.table.set(t.layer.redis, t.key, mapping)

        f1 = t.table.getfield(t.layer.redis, t.key, "f1")
        f2 = t.table.getfield(t.layer.redis, t.key, "f2")

        t.assertEqual(mapping["f1"], f1)
        t.assertEqual(str(mapping["f2"]), f2)

    def test_delete_data(t):
        mapping = {"f1": "cookie", "f2": 2343.2}
        t.table.set(t.layer.redis, t.key, mapping)

        t.table.delete(t.layer.redis, t.key)

        t.assertFalse(t.table.exists(t.layer.redis, t.key))
        t.assertFalse(t.table.exists(t.layer.redis, t.key, "f1"))
        t.assertFalse(t.table.exists(t.layer.redis, t.key, "f2"))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertIsNone(t.table.get(t.layer.redis, t.key))
        t.assertIsNone(t.table.getfield(t.layer.redis, t.key, "f1"))
        t.assertIsNone(t.table.getfield(t.layer.redis, t.key, "f2"))
