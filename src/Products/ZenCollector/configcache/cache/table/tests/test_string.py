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

from ..string import String


class TestStringTable(TestCase):
    """Test the String table class."""

    layer = RedisLayer

    def setUp(t):
        t.key = "app:cat1:foo:bar"
        t.table = String()

    def tearDown(t):
        del t.table

    def test_no_data(t):
        t.assertFalse(t.table.exists(t.layer.redis, t.key))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertIsNone(t.table.get(t.layer.redis, t.key))
        t.assertIsNone(t.table.delete(t.layer.redis, t.key))

    def test_add_data(t):
        data = "This is some data"

        t.table.set(t.layer.redis, t.key, data)

        t.assertTrue(t.table.exists(t.layer.redis, t.key))
        t.assertEqual(1, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertEqual(t.table.get(t.layer.redis, t.key), data)

    def test_add_different_data(t):
        key2 = "app:cat1:foo:bar2"
        data = "This is some data"
        pattern = "app:cat1:foo:*"

        t.table.set(t.layer.redis, t.key, data)
        t.table.set(t.layer.redis, key2, data)

        scan = sorted(t.table.scan(t.layer.redis, pattern))
        expected = sorted((t.key, key2))

        t.assertTrue(t.table.exists(t.layer.redis, t.key))
        t.assertTrue(t.table.exists(t.layer.redis, key2))
        t.assertListEqual(expected, scan)
        t.assertEqual(t.table.get(t.layer.redis, t.key), data)
        t.assertEqual(t.table.get(t.layer.redis, key2), data)

    def test_delete_data(t):
        data = "This is some data"

        t.table.set(t.layer.redis, t.key, data)
        t.table.delete(t.layer.redis, t.key)

        t.assertFalse(t.table.exists(t.layer.redis, t.key))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertIsNone(t.table.get(t.layer.redis, t.key))

    def test_mget(t):
        import string

        template = "app:cat1:foo:{}"
        keys = tuple(
            template.format(letter) for letter in string.ascii_lowercase
        )
        datum = tuple(
            "/the/letter/{}".format(letter)
            for letter in string.ascii_lowercase
        )
        table = String(mget_page_size=5)
        for key, value in zip(keys, datum):
            table.set(t.layer.redis, key, value)
        result = tuple(table.mget(t.layer.redis, *keys))
        t.assertEqual(len(string.ascii_lowercase), len(result))
        t.assertTupleEqual(tuple(zip(keys, datum)), result)
