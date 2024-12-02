##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import mock
import unittest

from functools import partial

from ..Executor import DynamicDeferredSemaphore, AsyncExecutor, reactor, defer


class TestDynamicDeferredSemaphore(unittest.TestCase):
    """Test the DynamicDeferredSemaphore class."""

    def test_init(t):
        s = DynamicDeferredSemaphore(0)
        t.assertEqual(s.limit, 0)
        t.assertEqual(s.tokens, 0)

    def test_bad_limit(t):
        with t.assertRaises(ValueError):
            DynamicDeferredSemaphore(-1)

    def test_change_limit(t):
        s = DynamicDeferredSemaphore(0)
        new_limit = 10
        s.limit = new_limit
        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, new_limit)

    def test_decrease_limit_no_available_token(t):
        original_limit = 5
        s = DynamicDeferredSemaphore(original_limit)

        for n in range(original_limit):
            d = s.acquire()
            t.assertTrue(d.called)
        # acquired: 5
        # released: 0
        t.assertEqual(s.tokens, 0)

        (d1, d2) = (s.acquire(), s.acquire())
        # acquired: 7
        # released: 0
        t.assertFalse(d1.called)
        t.assertFalse(d2.called)

        new_limit = 3
        s.limit = new_limit
        t.assertEqual(s.tokens, 0)

        s.release()  # acquired: 7  released: 1
        t.assertEqual(s.tokens, 0)
        t.assertFalse(d1.called)
        t.assertFalse(d2.called)

        s.release()  # acquired: 7  released: 2
        t.assertEqual(s.tokens, 0)
        t.assertFalse(d1.called)
        t.assertFalse(d2.called)

        s.release()  # acquired: 7  released: 3
        t.assertEqual(s.tokens, 0)
        t.assertTrue(d1.called)
        t.assertFalse(d2.called)

        s.release()  # acquired: 7  released: 4
        t.assertEqual(s.tokens, 0)
        t.assertTrue(d1.called)
        t.assertTrue(d2.called)

        s.release()  # acquired: 7  released: 5
        s.release()  # acquired: 7  released: 6
        s.release()  # acquired: 7  released: 7
        t.assertEqual(s.tokens, new_limit)

    def test_decrease_limit_with_available_token(t):
        # Start with a limit of 5
        original_limit = 5
        s = DynamicDeferredSemaphore(original_limit)

        # Acquire 4 tokens
        s.acquire()
        s.acquire()
        s.acquire()
        s.acquire()

        t.assertEqual(s.limit, original_limit)
        t.assertEqual(s.tokens, 1)

        # Lower the limit to 3
        new_limit = 3
        s.limit = new_limit

        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, 0)

        d1 = s.acquire()
        t.assertFalse(d1.called)

        s.release()
        t.assertFalse(d1.called)
        t.assertEqual(s.tokens, 0)

        s.release()
        t.assertTrue(d1.called)
        t.assertEqual(s.tokens, 0)

        s.release()
        s.release()
        s.release()
        t.assertEqual(s.tokens, s.limit)

    def test_simple_usage(t):
        # Test acquire/release without changing limit.
        limit = 5
        s = DynamicDeferredSemaphore(limit)
        d = s.acquire()
        t.assertTrue(d.called)
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, limit - 1)
        s.release()
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, limit)

    def test_limited_acquire(t):
        limit = 1
        s = DynamicDeferredSemaphore(limit)
        d1 = s.acquire()
        d2 = s.acquire()

        t.assertTrue(d1.called)
        t.assertFalse(d2.called)
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, 0)

        s.release()
        t.assertTrue(d2.called)
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, 0)

        s.release()
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, limit)

    def test_cancelled_wait(t):
        limit = 1
        s = DynamicDeferredSemaphore(limit)
        s.acquire()
        d2 = s.acquire()

        d2.cancel()
        s.release()
        t.assertEqual(s.limit, limit)
        t.assertEqual(s.tokens, limit)

    def test_increase_limit(t):
        limit = 1
        s = DynamicDeferredSemaphore(limit)
        s.acquire()
        d2 = s.acquire()
        d3 = s.acquire()

        new_limit = 2
        s.limit = new_limit

        t.assertTrue(d2.called)
        t.assertFalse(d3.called)
        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, 0)

        s.release()
        t.assertTrue(d3.called)
        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, 0)

        s.release()
        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, 1)

        s.release()
        t.assertEqual(s.limit, new_limit)
        t.assertEqual(s.tokens, new_limit)

    def test_infinity(t):
        s = DynamicDeferredSemaphore(0)

        d1 = s.acquire()
        t.assertTrue(d1.called)
        t.assertEqual(s.limit, 0)
        t.assertEqual(s.tokens, 0)

        d2 = s.acquire()
        t.assertTrue(d2.called)
        t.assertEqual(s.limit, 0)
        t.assertEqual(s.tokens, 0)

        s.release()
        s.release()
        s.release()
        t.assertEqual(s.limit, 0)
        t.assertEqual(s.tokens, 0)

    def test_change_to_and_from_infinite_limit(t):
        original_limit = 10
        s = DynamicDeferredSemaphore(original_limit)

        # 10 acquires
        for n in range(original_limit):
            s.acquire()
        t.assertEqual(s.tokens, 0)

        s.limit = 0
        t.assertEqual(s.tokens, 0)

        # 11th acquire
        d = s.acquire()
        t.assertTrue(d.called)
        t.assertEqual(s.tokens, 0)

        new_limit = 3
        s.limit = new_limit
        t.assertEqual(s.tokens, 0)

        # 8 releases
        for n in range(original_limit - new_limit + 1):
            s.release()
        t.assertEqual(s.tokens, 0)

        # acquisition attempt
        d2 = s.acquire()
        t.assertFalse(d2.called)

        # 9th release
        s.release()
        t.assertTrue(d2.called)
        t.assertEqual(s.tokens, 0)


class TestAsyncExecutor(unittest.TestCase):

    def test_init(t):
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        tokens = DynamicDeferredSemaphore(3)
        ae = AsyncExecutor(queue, tokens, log)
        t.assertFalse(ae.started)
        t.assertEqual(ae.limit, 3)
        t.assertEqual(ae.running, 0)
        t.assertEqual(ae.queued, 0)

    def test_change_limit(t):
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        tokens = DynamicDeferredSemaphore(3)
        ae = AsyncExecutor(queue, tokens, log)
        ae.limit = 5
        t.assertFalse(ae.started)
        t.assertEqual(ae.limit, 5)
        t.assertEqual(ae.limit, tokens.limit)
        t.assertEqual(ae.running, 0)
        t.assertEqual(ae.queued, 0)

    def test_submit(t):
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        tokens = DynamicDeferredSemaphore(3)
        ae = AsyncExecutor(queue, tokens, log)
        data = {}
        call = partial(_simple_call, data)
        d = ae.submit(call)
        t.assertFalse(d.called)
        t.assertEqual(ae.running, 0)
        t.assertEqual(ae.queued, 1)

    def test_execute_task(t):
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        tokens = DynamicDeferredSemaphore(3)
        ae = AsyncExecutor(queue, tokens, log)
        ae.start(reactor)

        data = {}
        call = partial(_simple_call, data)
        d = ae.submit(call)

        # Ask the reactor to run until there's nothing left to run.
        reactor.runUntilCurrent()

        t.assertTrue(d.called)
        t.assertEqual(ae.queued, 0)
        t.assertEqual(ae.running, 0)
        t.assertDictEqual(data, {"ran": True})

        # clean up
        ae.stop()

    def test_execute_async_task(t):
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        tokens = DynamicDeferredSemaphore(3)
        ae = AsyncExecutor(queue, tokens, log)

        args = _TaskData()
        call = partial(_complex_call, args.chan, args.data)
        d = ae.submit(call)

        ae.start(reactor)

        reactor.runUntilCurrent()

        args.chan.callback(True)
        reactor.runUntilCurrent()

        t.assertTrue(d.called)
        t.assertEqual(ae.queued, 0)
        t.assertEqual(ae.running, 0)
        t.assertDictEqual(args.data, {"r": True})

        # clean up
        ae.stop()

    def test_execute_multiple_async_tasks(t):
        tasks = (
            _TaskData(),
            _TaskData(),
            _TaskData(),
            _TaskData(),
        )
        task_count = remaining = len(tasks)

        # Note, the limit should be less than the number of tasks.
        log = mock.Mock(spec=logging.Logger)
        queue = defer.DeferredQueue()
        limit = task_count - 1
        tokens = DynamicDeferredSemaphore(limit)
        ae = AsyncExecutor(queue, tokens, log)

        for task in tasks:
            call = partial(_complex_call, task.chan, task.data)
            task.deferred = ae.submit(call)

        t.assertEqual(ae.queued, task_count)

        # Start the executor loop
        ae.start(reactor)

        remaining -= 1
        t.assertEqual(ae.queued, remaining)
        t.assertEqual(ae.running, 1)

        # Ask the reactor to run a count of "ticks" equal to the limit.
        # This should max out the executor's concurrency.
        for i in range(limit):
            reactor.runUntilCurrent()

        t.assertEqual(ae.queued, 1)
        t.assertEqual(ae.running, limit)

        # Unblock the _complex_call functions
        for i in range(limit):
            tasks[i].chan.callback(i)
            reactor.runUntilCurrent()

        # Run another tick
        reactor.runUntilCurrent()

        for i in range(limit):
            t.assertDictEqual(tasks[i].data, {"r": i})
            t.assertTrue(tasks[i].deferred.called)

        t.assertFalse(tasks[3].deferred.called)
        t.assertEqual(ae.queued, 0)
        t.assertEqual(ae.running, 1)

        # Unblock the last task
        tasks[3].chan.callback(3)

        # Go another tick of the reactor to finish the last task.
        reactor.runUntilCurrent()
        t.assertTrue(tasks[3].deferred.called)
        t.assertDictEqual(tasks[3].data, {"r": 3})

        t.assertEqual(ae.queued, 0)
        t.assertEqual(ae.running, 0)

        # clean up
        ae.stop()


class _TaskData(object):

    __slots__ = ("deferred", "data", "chan")

    def __init__(self):
        self.deferred = None
        self.data = {}
        self.chan = defer.Deferred()


def _simple_call(data):
    data["ran"] = True


@defer.inlineCallbacks
def _complex_call(d, data):
    r = yield d
    data["r"] = r
