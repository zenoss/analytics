##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


'''
Note that this is meant to be run from zopecctl using the "test" option. If you
would like to run these tests from python, simply to the following:

    python ZenUtils/Version.py
'''
import unittest
from zope.interface import implements
from zope.component.interfaces import IObjectEvent
from Products.Zuul.catalog.events import IndexingEvent

from OFS.SimpleItem import SimpleItem
from OFS.event import ObjectWillBeRemovedEvent
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zope.component import provideHandler
from zope.event import notify

from Products.ZenUtils.events import paused, pausedAndOptimizedIndexing


class MyEvent(object):
    pass


class IndexedObject(SimpleItem):
    def __init__(self, id):
        self.id = id


class UnindexingEvent(ObjectWillBeRemovedEvent):
    pass


class TestPauser(BaseTestCase):
  
    def test_pauser(self):
        SEEN = []
        handler = SEEN.append

        provideHandler(handler, (MyEvent,))
        notify(MyEvent())
        self.assertEquals(1, len(SEEN))
        with paused(handler):
            notify(MyEvent())
            self.assertEquals(1, len(SEEN))
        self.assertEquals(2, len(SEEN))
        notify(MyEvent())
        self.assertEquals(3, len(SEEN))

    def test_pausedIndexing(self):

        seen_indexed = []
        seen_unindexed = []

        def clear():
            while seen_indexed:
                seen_indexed.pop()
            while seen_unindexed:
                seen_unindexed.pop()

        def testOnIndexingEvent(ob, event):
            seen_indexed.append((ob, event))

        def testOnUnindexingEvent(ob, event):
            seen_unindexed.append((ob, event))

        provideHandler(testOnIndexingEvent, 
                       (IndexedObject, IndexingEvent))
        provideHandler(testOnUnindexingEvent, 
                       (IndexedObject, UnindexingEvent))

        ob1 = IndexedObject('1')

        # Verify events are wired correctly
        notify(IndexingEvent(ob1))
        notify(UnindexingEvent(ob1))
        self.assertEquals(1, len(seen_indexed))
        self.assertEquals(1, len(seen_unindexed))

        clear()

        # Basic functionality: single indexing event, all indexes
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1))
            self.assertEquals(0, len(seen_indexed))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertEquals(ob1, ob)
        self.assertTrue(not event.idxs)

        clear()

        # Removal, then index
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(UnindexingEvent(ob1))
            # Make sure the removal event has proceeded uninterrupted
            self.assertEquals(1, len(seen_unindexed))
            notify(IndexingEvent(ob1))

        self.assertEquals(1, len(seen_indexed))
        self.assertEquals(1, len(seen_unindexed))

        clear()

        # Index, then removal
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1))
            notify(UnindexingEvent(ob1))

        self.assertEquals(0, len(seen_indexed))
        self.assertEquals(1, len(seen_unindexed))

        clear()

        # 2 indexing events with all indexes
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1))
            notify(IndexingEvent(ob1))

        self.assertEquals(1, len(seen_indexed))

        clear()

        # 2 indexing events, specific first
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1, idxs=('path',)))
            notify(IndexingEvent(ob1))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertTrue(not event.idxs)

        clear()

        # 2 indexing events, specific second
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1))
            notify(IndexingEvent(ob1, idxs=('path',)))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertTrue(not event.idxs)

        clear()

        # 2 indexing events, both specific
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1, idxs=('path',)))
            notify(IndexingEvent(ob1, idxs=('uuid',)))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertIn('path', event.idxs)
        self.assertIn('uuid', event.idxs)
        self.assertEquals(2, len(event.idxs))

        clear()

        # 2 indexing events, update_metadata on first
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1, update_metadata=True))
            notify(IndexingEvent(ob1, update_metadata=False))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertTrue(event.update_metadata)

        clear()

        # 2 indexing events, update_metadata on second
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1, update_metadata=False))
            notify(IndexingEvent(ob1, update_metadata=True))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertTrue(event.update_metadata)

        clear()

        # 2 indexing events, update_metadata on neither
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1, update_metadata=False))
            notify(IndexingEvent(ob1, update_metadata=False))

        self.assertEquals(1, len(seen_indexed))
        ob, event = seen_indexed[0]
        self.assertFalse(event.update_metadata)

        clear()

        # 2 objects
        ob2 = IndexedObject('2')
        with pausedAndOptimizedIndexing(testOnIndexingEvent, 
                                        testOnUnindexingEvent):
            notify(IndexingEvent(ob1))
            notify(IndexingEvent(ob2))

        self.assertEquals(2, len(seen_indexed))
        ob_a, event = seen_indexed[0]
        ob_b, event = seen_indexed[1]
        self.assertTrue(ob_a != ob_b)
        self.assertIn(ob_a, (ob1, ob2))
        self.assertIn(ob_b, (ob1, ob2))

        clear()


def test_suite():
    return unittest.makeSuite(TestPauser)
