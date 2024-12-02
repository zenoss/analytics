##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Tests for the testing harness
"""

import unittest

from common import compare


class test_compare_string(unittest.TestCase):
    def test_None(self):
        s1 = "foo"
        s2 = None
        expected = ([], compare.Diff(s1, s2))
        self.assertEqual(expected, tuple(compare(s1, s2))[0])

    def test_same(self):
        s1 = "foo"
        s2 = "foo"
        expected = ()
        self.assertEqual(expected, tuple(compare(s1, s2)))

    def test_diff(self):
        s1 = "foo"
        s2 = "bar"
        expected = ([], compare.Diff(s1, s2))
        self.assertEqual(expected, tuple(compare(s1, s2))[0])

    def test_multiline_same(self):
        s1 = "foo\nbar\nbaz\n"
        s2 = "foo\nbar\nbaz\n"
        expected = ()
        self.assertEqual(expected, tuple(compare(s1, s2)))

    def test_multiline_diff(self):
        s1 = "foo\nbar\nbaz\n"
        s2 = "foo\nBAR\nbaz\n"
        expected = ([], None)
        actual = tuple(compare(s1, s2))[0]
        diff = "\n".join(actual[-1])
        self.assertEqual(expected[:-1], actual[:-1])
        self.assertIn("-bar", diff)
        self.assertIn("+BAR", diff)


class test_compare_dict(unittest.TestCase):
    def test_none(self):
        d1 = {"a": 1, "b": 2}
        d2 = None
        expected = ([], compare.Diff(d1, d2))
        self.assertEqual(expected, tuple(compare(d1, d2))[0])

    def test_same(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 1, "b": 2}
        expected = ()
        self.assertEqual(expected, tuple(compare(d1, d2)))

    def test_value(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 1, "b": 22}
        expected = (
            (["b"], compare.Diff(d1["b"], d2["b"])),
        )
        actual = tuple(compare(d1, d2))
        self.assertEqual(expected, actual)

    def test_size(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 1, "b": 2, "c": 3}
        expected = (
            (["c"], compare.Diff(compare.missingKey, d2["c"])),
        )
        actual = tuple(compare(d1, d2))
        self.assertEqual(expected, actual)

    def test_case_same(self):
        """case insensitive keys, use value of "most-lowercase" key"""
        d1 = dict(AA=1, Aa=2, aA=3, aa=4, bB=6, BB=7)
        d2 = dict(Aa=4, BB=6)
        expected = ()
        self.assertEqual(expected, tuple(compare(d1, d2)))

    def test_case_diff(self):
        """case insensitive keys, use value of "most-lowercase" key"""
        d1 = dict(AA=1, Aa=2, aA=3, aa=22, bB=6, BB=7)
        d2 = dict(Aa=4, BB=6)
        expected = (["aa"], compare.Diff(d1["aa"], d2["Aa"]))
        self.assertEqual(expected, tuple(compare(d1, d2))[0])

    def test_multiple_diffs(self):
        d1 = {"a": 1, "b": 2, "c": 3, "d": 4}
        d2 = {"a": 1, "b": 22, "c": 3, "d": 44, "e": 5}
        expected = (
            (["b"], compare.Diff(d1["b"], d2["b"])),
            (["d"], compare.Diff(d1["d"], d2["d"])),
            (["e"], compare.Diff(compare.missingKey, d2["e"])),
        )
        actual = tuple(compare(d1, d2))
        self.assertEqual(expected, actual)


class test_compare_list(unittest.TestCase):
    def test_same(self):
        l1 = [1, 2, 3]
        l2 = [1, 2, 3]
        expected = ()
        self.assertEqual(expected, tuple(compare(l1, l2)))

    def test_none(self):
        l1 = [1, 2, 3]
        l2 = None
        expected = ([], compare.Diff(l1, l2))
        self.assertEqual(expected, tuple(compare(l1, l2))[0])

    def test_value(self):
        l1 = [1, 2, 3]
        l2 = [1, 22, 3]
        expected = (
            ([1], compare.Diff(l1[1], l2[1])),
        )
        self.assertEqual(expected, tuple(compare(l1, l2)))

    def test_size(self):
        l1 = [1, 2, 3]
        l2 = [1, 2]
        expected = ([], compare.Diff(l1, l2))
        actual = tuple(compare(l1, l2))[0]
        self.assertEqual(expected, actual)

    def test_multiple_diffs(self):
        l1 = [1, 2, 3, 4, 5]
        l2 = [1, 22, 3, 44, 5]
        expected = (
            ([1], compare.Diff(l1[1], l2[1])),
            ([3], compare.Diff(l1[3], l2[3])),
        )
        self.assertEqual(expected, tuple(compare(l1, l2)))
