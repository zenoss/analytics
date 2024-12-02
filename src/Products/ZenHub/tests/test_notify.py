from unittest import TestCase
from mock import Mock, create_autospec, patch, call

from Products.ZenHub.notify import (
    NotifyItem,
    BatchNotifier,
    defer,
    BATCH_NOTIFIER,
)

PATH = {"notify": "Products.ZenHub.notify"}


class NotifyItemTest(TestCase):
    def test_init(self):
        device_class_uid = "some uuid"
        subdevices = ["list of", "devices"]

        notify_item = NotifyItem(device_class_uid, subdevices)

        self.assertEqual(notify_item.device_class_uid, device_class_uid)
        self.assertEqual(notify_item.subdevices, subdevices)
        # filtered defaults to false
        self.assertEqual(notify_item.filtered, False)
        self.assertEqual(notify_item.notify_functions, {})
        self.assertEqual(notify_item.d, None)
        # filtered defaults to false


class BatchNotifierTest(TestCase):
    def setUp(self):
        self.bn = BatchNotifier()
        self.item = Mock(spec_set=NotifyItem("device_class", "subdevices"))

    def test_init(self):
        BatchNotifier()

    def test_notify_subdevices(self):
        device_class = "device_class"
        service_uid = "service_uid"
        notify_function = "notify_function"
        filter = None

        item = Mock(spec_set=NotifyItem(device_class, "subdevices"))
        item.notify_functions = {}
        # Mock the find_or_create_item method
        self.bn._find_or_create_item = create_autospec(
            self.bn._find_or_create_item, return_value=item
        )

        self.bn.notify_subdevices(
            device_class, service_uid, notify_function, filter=filter
        )

        self.bn._find_or_create_item.assert_called_with(device_class, filter)
        self.assertEqual(item.notify_functions[service_uid], notify_function)

    def test_find_or_create_item(self):
        """search batch_notifier._queue for the device and return it
        if its not found in _queue, create a new instance, append it to _queue
        and return it
        """
        device_class = Mock(name="device_class", spec_set=["getPrimaryId"])
        filter = Mock(name="filter", spec_set=[])
        self.item.device_class_uid = device_class.getPrimaryId()
        self.item.filtered = False
        self.bn._queue.append(self.item)

        self.assertEqual(
            self.item.device_class_uid, device_class.getPrimaryId()
        )
        ret = self.bn._find_or_create_item(device_class, filter)

        self.assertEqual(ret, self.item)

    def test_find_or_create_item_not_in_queue(self):
        """if the item is not found in _queue,
        create a new item, append it to _queue, and return it
        if the queue was empty, call batch_notifier._call_later with a deffered
        """
        device_class = Mock(
            name="device_class", spec_set=["getPrimaryId", "getSubDevicesGen"]
        )
        filter = Mock(name="filter", spec_set=[])
        self.bn._call_later = create_autospec(self.bn._call_later)

        item = self.bn._find_or_create_item(device_class, filter)

        self.assertIn(item, self.bn._queue)
        self.bn._call_later.assert_called_with(item.d)

        self.assertIsInstance(item, NotifyItem)
        self.assertIsInstance(item.d, defer.Deferred)
        self.assertEqual(item.device_class_uid, device_class.getPrimaryId())
        self.assertEqual(item.subdevices, device_class.getSubDevicesGen())

    @patch(
        "{notify}.defer.Deferred".format(**PATH),
        name="Deferred",
        autospec=True,
    )
    def test_create_deferred(self, Deferred):
        """returns a deferred
        with batch_notifier._callback and ._errback attached
        """
        ret = self.bn._create_deferred()

        self.assertEqual(ret, Deferred())
        ret.addCallback.assert_called_with(self.bn._callback)
        ret.addErrback.assert_called_with(self.bn._errback)

    @patch("{notify}.reactor".format(**PATH), name="reactor", autospec=True)
    def test_call_later(self, reactor):
        d = Mock(defer.Deferred())
        self.bn._call_later(d)

        reactor.callLater.assert_called_with(
            BATCH_NOTIFIER._DELAY, d.callback, None
        )

    def test_switch_to_next_item(self):
        self.bn._queue.append(self.item)
        self.bn._switch_to_next_item()

        self.assertEqual(self.bn._current_item, self.item)

    def test_switch_to_next_item_empty_queue(self):
        """if the queue is empty, set _current_item to None"""
        self.bn._switch_to_next_item()

        self.assertEqual(self.bn._current_item, None)

    def test_call_notify_functions(self):
        """call each notify_function for the _current_item
        with the device parameter
        """
        notify_function_a = Mock(name="notify_function_a")
        notify_function_b = Mock(name="notify_function_b")
        self.item.notify_functions = {
            "service_uid": notify_function_a,
            "service_uid_b": notify_function_b,
        }
        self.bn._current_item = self.item
        device = Mock(name="device", spec_set=[])

        self.bn._call_notify_functions(device)

        for notify_function in self.item.notify_functions.values():
            notify_function.assert_called_with(device)

    def test_callback(self):
        """big recursive callback, should be refactored using inlineCallbacks
        itterate over the list of items in _queue
        calling each notify_function on each item
        when BatchNotifier._BATCH_SIZE items have been processed
        pass the current item's deferred to _call_later
        """
        self.bn._call_notify_functions = create_autospec(
            self.bn._call_notify_functions
        )
        self.bn._call_later = create_autospec(self.bn._call_later)
        BatchNotifier._BATCH_SIZE = 100
        items = [
            Mock(
                spec_set=NotifyItem("device_class", "subdevices"),
                name="item_%s" % x,
            )
            for x in ("a", "b", "c")
        ]

        for item in items:
            item.subdevices = [
                Mock(name="device_%s" % x, spec_set=[])
                for x in ("a", "b", "c")
            ]
            self.bn._queue.appendleft(item)

        self.bn._callback(result=None)

        # WARNING: It looks like the intent was to continue processing the
        # next item in the queue, until the batchsize is met
        # however, the current implentation always stops after a single item
        self.bn._call_notify_functions.assert_has_calls(
            [call(device) for device in items[0].subdevices]
        )
        """
        self.bn._call_notify_functions.assert_has_calls([
            call(device)
            for device in item.subdevices
            for item in items
        ])
        """

        self.bn._call_later.assert_called_with(items[1].d)

    def test_callback_batch_size(self):
        """If item.subdevices exceeds batch size the intent was probably to
        process all of the items subdevices in multiple batches.
        however, the current version skips the extra devices, and re-schedules
        the item to be processed again.
        """
        self.bn._call_notify_functions = create_autospec(
            self.bn._call_notify_functions
        )
        self.bn._call_later = create_autospec(self.bn._call_later)
        BatchNotifier._BATCH_SIZE = 1

        self.item.subdevices = [
            Mock(name="device_%s" % x, spec_set=[]) for x in ("a", "b", "c")
        ]
        self.bn._queue.append(self.item)

        self.bn._callback(result=None)

        # WARNING: unintended behavior
        # the same item will be reprocessed repeatedly
        self.bn._call_notify_functions.assert_called_with(
            self.item.subdevices[0]
        )
        self.bn._call_later.assert_called_with(self.item.d)

    def test_errback(self):
        """currently logs the exception without handling it"""
        pass

    @patch("{notify}.defer.DeferredList".format(**PATH), autospec=True)
    def test_stop(self, DeferredList):
        self.bn._queue.append(self.item)
        ret = self.bn.stop()
        self.assertTrue(self.bn._stopping)

        self.assertEqual(ret, DeferredList.return_value)
        DeferredList.assert_called_with([item.d for item in self.bn._queue])

    @patch("{notify}.defer.Deferred".format(**PATH), autospec=True)
    def test_whenEmpty(self, Deferred):
        ret = self.bn.whenEmpty()

        Deferred.return_value.callback.assert_called_with(None)
        self.assertEqual(ret, Deferred.return_value)

    @patch("{notify}.defer.Deferred".format(**PATH), autospec=True)
    def test_whenEmpty_is_not_empty(self, Deferred):
        self.bn._queue.append(self.item)
        ret = self.bn.whenEmpty()

        self.assertEqual(self.bn._empty, ret)

        # We cannot check that it was called with a function defined inside
        # of this method
        # Deferred.return_value.addCallback.assert_called_with()
        self.assertEqual(ret, Deferred.return_value)
