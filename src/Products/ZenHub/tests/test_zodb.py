from mock import sentinel, patch
from unittest import TestCase

from zope.interface.verify import verifyObject

from Products.ZenHub.zodb import (
    DeletionEvent,
    IDeletionEvent,
    InvalidationEvent,
    IUpdateEvent,
    ObjectEvent,
    onDelete,
    onUpdate,
    UpdateEvent,
)

PATH = {"src": "Products.ZenHub.zodb"}


class InvalidationEventTest(TestCase):
    def test___init__(t):
        obj = sentinel.object
        oid = sentinel.oid

        iet = InvalidationEvent(obj, oid)

        t.assertIsInstance(iet, ObjectEvent)
        t.assertEqual(iet.oid, oid)


class UpdateEventTest(TestCase):
    def test_implements_IUpdateEvent(t):
        # the class Implements the Interface
        t.assertTrue(IUpdateEvent.implementedBy(UpdateEvent))

    def test___init__(t):
        obj = sentinel.object
        oid = sentinel.oid

        update_event = UpdateEvent(obj, oid)

        # the object provides the interface
        t.assertTrue(IUpdateEvent.providedBy(update_event))
        # Verify the object implments the interface properly
        verifyObject(IUpdateEvent, update_event)


class DeletionEventTest(TestCase):
    def test_implements_IDeletionEvent(t):
        # the class Implements the Interface
        t.assertTrue(IDeletionEvent.implementedBy(DeletionEvent))

    def test___init__(t):
        obj = sentinel.object
        oid = sentinel.oid

        deletion_event = DeletionEvent(obj, oid)

        # the object provides the interface
        t.assertTrue(IDeletionEvent.providedBy(deletion_event))
        # Verify the object implments the interface properly
        verifyObject(IDeletionEvent, deletion_event)


class _listener_decorator_factoryTest(TestCase):

    """Used to create decorators
    that register class methods as event handlers
    """

    @patch("{src}.provideHandler".format(**PATH), autospec=True)
    def test_onUpdate_decorator(t, provideHandler):
        """Decorator for a class method
        causes the decorated method to run when an update event
        of the specified type (onUpdate arg) fires
        event type examples: PerformanceConf, ZenPack, Device
        """
        eventtype = sentinel.eventtype  # EX: PerformanceConf

        class MyClass(object):
            @onUpdate(eventtype)
            def eventtype_update_handler(self, obj, event):
                pass

        mc = MyClass()

        provideHandler.assert_called_with(
            mc.eventtype_update_handler, (eventtype, IUpdateEvent)
        )

    @patch("{src}.provideHandler".format(**PATH), autospec=True)
    def test_onDeleted_decorator(t, provideHandler):
        """Decorator for a class method
        causes the decorated method to run when a deleted event
        of the specified type (onUpdate arg) fires
        """
        eventtype = sentinel.eventtype

        class MyClass(object):
            @onDelete(eventtype)
            def eventtype_deleted_handler(self, obj, event):
                pass

        mc = MyClass()

        provideHandler.assert_called_with(
            mc.eventtype_deleted_handler, (eventtype, IDeletionEvent)
        )
