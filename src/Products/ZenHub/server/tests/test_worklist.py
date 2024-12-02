##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import collections

from itertools import cycle
from mock import NonCallableMock
from unittest import TestCase

from ..worklist import ZenHubWorklist

PATH = {"src": "Products.ZenHub.server.worklist"}


class _SimpleSelector(collections.Iterator):
    """Helper class that provides a selector for ZenHubWorklist."""

    def __init__(self, priorities):
        self.__priorities = priorities
        self.__iter = cycle(priorities)
        self.ignored = None

    @property
    def priorities(self):
        return self.__priorities

    @property
    def available(self):
        return tuple(p for p in self.__priorities if p != self.ignored)

    def next(self):  # noqa: A003
        return next(p for p in self.__iter if p != self.ignored)


class ZenHubWorklistTest(TestCase):  # noqa: D101
    def setUp(self):
        self.pvalues = ("a", "b")
        self.selection = _SimpleSelector(self.pvalues)
        self.worklist = ZenHubWorklist(self.selection)

    def test_initial_state(self):
        self.assertEqual(0, len(self.worklist))
        ret = self.worklist.pop()
        # empty worklists return an uncalled deferred
        self.assertFalse(ret.called)

    def test_push(self):
        item = NonCallableMock(spec_set=[])
        self.worklist.push("a", item)
        self.assertEqual(1, len(self.worklist))
        popped_item = self.worklist.pop()
        self.assertEqual(item, popped_item.result)
        self.assertEqual(0, len(self.worklist))

    def test_push_later(self):
        # Ask for an item from the worklist
        ret = self.worklist.pop()
        # It is an empy, uncalled deferred
        self.assertFalse(ret.called)
        # Push an item to the worklist later
        item = NonCallableMock(spec_set=[])
        self.worklist.push("a", item)
        # now the item we got before, will be called,
        # and contain the item we pushed
        self.assertTrue(ret.called)
        self.assertEqual(item, ret.result)

    def test_pushfront(self):
        item1 = NonCallableMock(spec_set=[])
        self.worklist.pushfront("a", item1)
        item2 = NonCallableMock(spec_set=[])
        self.worklist.pushfront("a", item2)

        popped_item = self.worklist.pop()
        self.assertEqual(item2, popped_item.result)
        self.assertEqual(1, len(self.worklist))

    def test_push_bad_priority(self):
        item = NonCallableMock(spec_set=[])
        with self.assertRaises(KeyError):
            self.worklist.push("bad", item)
        self.assertEqual(0, len(self.worklist))

        # returns an uncalled deferred
        ret = self.worklist.pop()
        self.assertFalse(ret.called)

    def test_pushfront_bad_priority(self):
        item = NonCallableMock(spec_set=[])
        with self.assertRaises(KeyError):
            self.worklist.pushfront("bad", item)
        self.assertEqual(0, len(self.worklist))

        # returns an uncalled deferred
        ret = self.worklist.pop()
        self.assertFalse(ret.called)

    def test_multiple_priorities(self):
        item1 = NonCallableMock(spec_set=[])
        self.worklist.push("a", item1)
        item2 = NonCallableMock(spec_set=[])
        self.worklist.push("b", item2)
        self.assertEqual(2, len(self.worklist))

        items = []
        items.append(self.worklist.pop().result)
        items.append(self.worklist.pop().result)
        self.assertEqual([item1, item2], items)

    def test_when_available_differs(self):
        """The ignored item1, is not returned from the worklist"""
        self.selection.ignored = "a"
        item1 = NonCallableMock(spec_set=[])
        self.worklist.push("a", item1)
        item2 = NonCallableMock(spec_set=[])
        self.worklist.push("b", item2)
        self.assertEqual(2, len(self.worklist))

        # item2 is returned as the result of the deferred
        ret = self.worklist.pop()
        self.assertTrue(ret.called)
        self.assertEqual(ret.result, item2)
        # the next returned value is an uncalled deferred, not item1
        ret = self.worklist.pop()
        self.assertFalse(ret.called)
