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

from ..serialization import without_unicode


class WithoutUnicodeTest(TestCase):
    """Test the without_unicode serialization functions."""

    def test_empty_set(t):
        data = {}
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertDictEqual(data, loaded)

    def test_simple_dict(t):
        data = {"a": "/"}
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertDictEqual(data, loaded)

    def test_lists(t):
        data = ["a", "b"]
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertSequenceEqual(data, loaded)

    def test_nested_lists(t):
        data = ["a", ["b", "c"]]
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertSequenceEqual(data, loaded)

    def test_nested_dicts(t):
        data = {
            "a": {
                "b": 3,
                "c": {
                    "d": "blah",
                },
            },
        }
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertSequenceEqual(data, loaded)

    def test_variety(t):
        data = {
            "id": "woeijfoejf",
            "args": ["a", ["c", "f"]],
            "info": [{"a": 1}, {"b": {"d": "y", "e": 42}}],
        }
        dumped = without_unicode.dump(data)
        loaded = without_unicode.load(dumped)
        t.assertIsInstance(dumped, str)
        t.assertDictEqual(data, loaded)
