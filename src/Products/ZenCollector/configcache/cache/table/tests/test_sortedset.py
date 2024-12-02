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

from ..sortedset import SortedSet


class TestSortedSetTable(TestCase):
    """Test the SortedSet table class."""

    layer = RedisLayer

    def setUp(t):
        t.key = "app:cat1:foo:bar"
        t.table = SortedSet()

    def tearDown(t):
        del t.table

    def test_no_data(t):
        value = "c"
        t.assertFalse(t.table.exists(t.layer.redis, t.key, value))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertEqual(0, len(tuple(t.table.range(t.layer.redis, t.key))))
        t.assertIsNone(t.table.score(t.layer.redis, t.key, value))
        t.assertIsNone(t.table.delete(t.layer.redis, t.key, value))

    def test_add_data(t):
        value = "baz"
        score = 10.5

        t.table.add(t.layer.redis, t.key, value, score)

        scan = tuple(t.table.scan(t.layer.redis, t.key))
        rng = tuple(t.table.range(t.layer.redis, t.key))
        expected = ((t.key, value, score),)

        t.assertTrue(t.table.exists(t.layer.redis, t.key, value))
        t.assertTupleEqual(expected, scan)
        t.assertTupleEqual(expected, rng)
        t.assertEqual(t.table.score(t.layer.redis, t.key, value), score)

    def test_add_more_data(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        scan = tuple(t.table.scan(t.layer.redis, t.key))
        rng = tuple(t.table.range(t.layer.redis, t.key))
        expected = (
            (t.key, data[0][0], data[0][1]),
            (t.key, data[1][0], data[1][1]),
        )

        t.assertTrue(t.table.exists(t.layer.redis, t.key, data[0][0]))
        t.assertTrue(t.table.exists(t.layer.redis, t.key, data[1][0]))
        t.assertTupleEqual(expected, scan)
        t.assertTupleEqual(expected, rng)
        t.assertEqual(
            t.table.score(t.layer.redis, t.key, data[0][0]), data[0][1]
        )
        t.assertEqual(
            t.table.score(t.layer.redis, t.key, data[1][0]), data[1][1]
        )

    def test_add_different_data(t):
        key2 = "app:cat1:foo:bar2"
        pattern = "app:cat1:foo:*"
        data1 = ("baz", 10.5)
        data2 = ("fab", 12.23)

        t.table.add(t.layer.redis, t.key, data1[0], data1[1])
        t.table.add(t.layer.redis, key2, data2[0], data2[1])

        scan = tuple(
            sorted(
                t.table.scan(t.layer.redis, pattern), key=lambda x: x[1]
            )
        )
        rng = tuple(
            sorted(
                t.table.range(t.layer.redis, pattern),
                key=lambda x: x[1],
            )
        )
        expected = (
            (t.key, data1[0], data1[1]),
            (key2, data2[0], data2[1]),
        )

        t.assertTrue(t.table.exists(t.layer.redis, t.key, data1[0]))
        t.assertTrue(t.table.exists(t.layer.redis, key2, data2[0]))
        t.assertTupleEqual(expected, scan)
        t.assertTupleEqual(expected, rng)
        t.assertEqual(
            t.table.score(t.layer.redis, t.key, data1[0]), data1[1]
        )
        t.assertEqual(
            t.table.score(t.layer.redis, key2, data2[0]), data2[1]
        )

    def test_minscore(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(t.table.range(t.layer.redis, t.key, minscore=11))
        expected = ((t.key, data[1][0], data[1][1]),)

        t.assertTupleEqual(expected, rng)

    def test_minscore_equality(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(t.table.range(t.layer.redis, t.key, minscore=12.23))
        expected = ((t.key, data[1][0], data[1][1]),)

        t.assertTupleEqual(expected, rng)

    def test_maxscore(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(t.table.range(t.layer.redis, t.key, maxscore=11))
        expected = ((t.key, data[0][0], data[0][1]),)

        t.assertTupleEqual(expected, rng)

    def test_maxscore_equality(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(t.table.range(t.layer.redis, t.key, maxscore=10.5))
        expected = ((t.key, data[0][0], data[0][1]),)

        t.assertTupleEqual(expected, rng)

    def test_range_full_bounding(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(
            t.table.range(t.layer.redis, t.key, minscore=11, maxscore=13)
        )
        expected = ((t.key, data[1][0], data[1][1]),)

        t.assertTupleEqual(expected, rng)

    def test_range_inverted_range(t):
        data = [("baz", 10.5), ("fab", 12.23)]

        t.table.add(t.layer.redis, t.key, data[0][0], data[0][1])
        t.table.add(t.layer.redis, t.key, data[1][0], data[1][1])

        rng = tuple(
            t.table.range(t.layer.redis, t.key, maxscore=11, minscore=13)
        )
        expected = ()
        t.assertTupleEqual(expected, rng)

    def test_delete_data(t):
        value = "baz"
        score = 10.5

        t.table.add(t.layer.redis, t.key, value, score)
        t.table.delete(t.layer.redis, t.key, value)

        t.assertFalse(t.table.exists(t.layer.redis, t.key, value))
        t.assertEqual(0, len(tuple(t.table.scan(t.layer.redis, t.key))))
        t.assertIsNone(t.table.score(t.layer.redis, t.key, value))
