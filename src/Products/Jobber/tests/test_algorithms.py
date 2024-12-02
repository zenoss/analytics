##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from unittest import TestCase

from ..utils.algorithms import partition


class PartitionTest(TestCase):
    """Test the partition function."""

    def test_no_data(t):
        expected = ([], [])
        actual = partition([], lambda x: True)
        t.assertTupleEqual(expected, actual)

    def test_always_true(t):
        data = [1, 2, 3]
        expected = (data, [])
        actual = partition(data, lambda x: True)
        t.assertTupleEqual(expected, actual)

    def test_always_false(t):
        data = [1, 2, 3]
        expected = ([], data)
        actual = partition(data, lambda x: False)
        t.assertTupleEqual(expected, actual)

    def test_bad_source(t):
        with t.assertRaises(TypeError):
            partition(1, lambda x: True)

    def test_bad_predicate(t):
        with t.assertRaises(TypeError):
            partition([1], lambda: True)

    def test_nominal(t):
        data = [1, 2, 3, 4]
        expected = ([1, 3], [2, 4])
        actual = partition(data, lambda x: x % 2 != 0)
        t.assertTupleEqual(expected, actual)

    def test_stable_ordering(t):
        data = [2, 3, 1, 4]
        expected = ([3, 1], [2, 4])
        actual = partition(data, lambda x: x % 2 != 0)
        t.assertTupleEqual(expected, actual)

    def test_source_read_once(t):
        data = (1, 2, 3, 4)
        expected = ([1, 3], [2, 4])
        actual = partition(data, lambda x: x % 2 != 0)
        t.assertTupleEqual(expected, actual)
