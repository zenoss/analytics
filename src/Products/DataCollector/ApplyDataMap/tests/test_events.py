##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase

from zope.interface.verify import verifyObject

from ..events import (
    DatamapAddEvent,
    DatamapAppliedEvent,
    DatamapUpdateEvent,
    IDatamapAddEvent,
    IDatamapAppliedEvent,
    IDatamapEvent,
    IDatamapUpdateEvent,
)


class TestDatamapAddEvent(TestCase):
    def test_implements_IDatamapAddEvent(t):
        datamap_add_event = DatamapAddEvent("dmd", "objectmap", "target")

        verifyObject(IDatamapEvent, datamap_add_event)
        verifyObject(IDatamapAddEvent, datamap_add_event)

        # the class implements the interface
        t.assertTrue(IDatamapAddEvent.implementedBy(DatamapAddEvent))
        # the object provides the interface
        t.assertTrue(IDatamapAddEvent.providedBy(datamap_add_event))
        t.assertEqual(datamap_add_event.dmd, "dmd")
        t.assertEqual(datamap_add_event.objectmap, "objectmap")
        t.assertEqual(datamap_add_event.target, "target")


class TestDatamapUpdateEvent(TestCase):
    def test_implements_IDatamapUpdateEvent(t):
        datamap_update_event = DatamapUpdateEvent("dmd", "objectmap", "target")

        verifyObject(IDatamapEvent, datamap_update_event)
        verifyObject(IDatamapUpdateEvent, datamap_update_event)

        # the class implements the interface
        t.assertTrue(IDatamapUpdateEvent.implementedBy(DatamapUpdateEvent))
        # the object provides the interface
        t.assertTrue(IDatamapUpdateEvent.providedBy(datamap_update_event))
        t.assertEqual(datamap_update_event.dmd, "dmd")
        t.assertEqual(datamap_update_event.objectmap, "objectmap")
        t.assertEqual(datamap_update_event.target, "target")


class TestDatamapAppliedEvent(TestCase):
    def test_implements_IDatamapUpdateEvent(t):
        datamap_applied_event = DatamapAppliedEvent("datamap")

        verifyObject(IDatamapAppliedEvent, datamap_applied_event)

        # the class implements the interface
        t.assertTrue(IDatamapAppliedEvent.implementedBy(DatamapAppliedEvent))
        # the object provides the interface
        t.assertTrue(IDatamapAppliedEvent.providedBy(datamap_applied_event))
        t.assertEqual(datamap_applied_event.datamap, "datamap")
