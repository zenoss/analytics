##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import MagicMock, Mock, patch
from twisted.internet import defer
from twisted.python.failure import Failure

from Products.ZenHub.server.service import ServiceCall

from ..worker import Worker
from ..workerpool import (
    WorkerPool,
    WorkerAvailabilityQueue,
)

PATH = {"src": "Products.ZenHub.server.workerpool"}


class WorkerPoolTest(TestCase):  # noqa: D101
    def setUp(t):
        t.queue = "default"
        t.pool = WorkerPool(t.queue)
        t.worker1 = MagicMock(Worker, autospec=True)
        t.worker1.name = "default_1"
        t.worker2 = MagicMock(Worker, autospec=True)
        t.worker2.name = "default_2"

    def test_name_property(t):
        t.assertEqual(t.queue, t.pool.name)

    def test_add_workers_not_ready(t):
        t.pool.add(t.worker1)
        t.assertIn(t.worker1, t.pool)

        t.pool.add(t.worker2)
        t.assertIn(t.worker2, t.pool)

        t.assertEqual(2, len(t.pool))
        t.assertEqual(0, t.pool.available)

    def test_add_worker_twice_not_ready(t):
        t.pool.add(t.worker1)
        t.assertIn(t.worker1, t.pool)

        t.pool.add(t.worker1)
        t.assertIn(t.worker1, t.pool)

        t.assertEqual(len(t.pool), 1)
        t.assertEqual(0, t.pool.available)

    def test_ready(t):
        t.pool.add(t.worker1)
        t.pool.add(t.worker2)

        t.pool.ready(t.worker1)
        t.assertEqual(1, t.pool.available)
        t.assertIn(t.worker1, t.pool)

        t.pool.ready(t.worker2)
        t.assertEqual(2, t.pool.available)
        t.assertIn(t.worker2, t.pool)

    def test_ready_after_replace(t):
        worker_replacement = MagicMock(Worker, autospec=True)
        worker_replacement.name = t.worker1.name

        t.pool.add(t.worker1)
        t.pool.ready(t.worker1)
        t.assertIn(t.worker1, t.pool)
        t.assertEqual(1, t.pool.available)
        t.assertNotIn(worker_replacement, t.pool)

        t.pool.add(worker_replacement)
        t.assertEqual(len(t.pool), 1)
        t.assertIn(worker_replacement, t.pool)
        t.assertNotIn(t.worker1, t.pool)
        t.assertEqual(0, t.pool.available)

        t.pool.ready(t.worker1)
        t.assertEqual(1, t.pool.available)

    def test_remove_without_ready(t):
        t.pool.add(t.worker1)
        t.pool.add(t.worker2)
        t.assertEqual(len(t.pool), 2)

        t.pool.remove(t.worker1)
        t.assertNotIn(t.worker1, t.pool)
        t.assertIn(t.worker2, t.pool)
        t.assertEqual(len(t.pool), 1)

        t.pool.remove(t.worker2)
        t.assertNotIn(t.worker1, t.pool)
        t.assertNotIn(t.worker2, t.pool)
        t.assertEqual(len(t.pool), 0)

    def test_available(t):
        t.assertEqual(t.pool.available, 0)

        t.pool.add(t.worker1)
        t.assertEqual(t.pool.available, 0)

        t.pool.ready(t.worker1)
        t.assertEqual(t.pool.available, 1)

        t.pool.remove(t.worker1)
        t.assertEqual(t.pool.available, 0)

    def test_iter_protocol(t):
        w = next(iter(t.pool), None)
        t.assertIsNone(w)

        t.pool.add(t.worker1)
        w = next(iter(t.pool), None)
        t.assertIsNotNone(w)
        t.assertIsInstance(w, Worker)
        t.assertIs(w, t.worker1)

    def test_hire(t):
        t.worker1.remote.callRemote.return_value = defer.succeed("pong")

        t.pool.add(t.worker1)
        t.pool.ready(t.worker1)

        def assign(x, v):
            x.value = v

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertIsInstance(hired_worker, Worker)
        t.assertIs(hired_worker, t.worker1)
        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 1)

    def test_remove_after_hire(t):
        t.pool.add(t.worker1)
        t.pool.ready(t.worker1)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        dfr = t.pool.hire()
        hired_worker = dfr.result
        t.pool.remove(hired_worker)

        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 0)

    def test_hire_no_workers(t):
        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 0)

        dfr = t.pool.hire()
        # The deferred returned from the pool has not been called
        t.assertFalse(dfr.called)

    def test_wait_for_available_worker(t):
        dfr = t.pool.hire()
        # The deferred returned from the pool has not been called
        t.assertFalse(dfr.called)

        # a worker becomes available
        t.worker1.remote.callRemote.return_value = defer.succeed("pong")
        t.pool.add(t.worker1)

        # Still not called because 'ready' hasn't been called.
        t.assertFalse(dfr.called)

        t.pool.ready(t.worker1)

        # the deferred is called, and worker_ref is its result
        t.assertTrue(dfr.called)
        worker = dfr.result
        t.assertIsInstance(worker, Worker)
        # the reference object contains the worker
        t.assertIs(worker, t.worker1)

    def test_hire_no_available_workers(t):
        with patch.object(
            WorkerPool, "available", return_value=0
        ) as available:
            pool = WorkerPool(t.queue)
            pool.add(t.worker1)

            available.__len__.return_value = 0
            t.assertEqual(len(pool), 1)

            dfr = t.pool.hire()
            t.assertFalse(dfr.called)

            available.pop.assert_not_called()

    def test_ready_after_hire(t):
        t.pool.add(t.worker1)
        t.pool.ready(t.worker1)

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertEqual(0, t.pool.available)
        t.assertEqual(1, len(t.pool))

        t.pool.ready(hired_worker)

        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

    def test_ready_retired_worker(t):
        t.pool.add(t.worker1)
        t.pool.ready(t.worker1)

        dfr = t.pool.hire()
        hired_worker = dfr.result

        t.assertEqual(t.pool.available, 0)
        t.assertEqual(len(t.pool), 1)

        t.pool.remove(t.worker1)

        worker2 = MagicMock(Worker, autospec=True)
        worker2.name = t.worker1.name

        t.pool.add(worker2)
        t.pool.ready(worker2)
        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

        t.pool.ready(hired_worker)
        t.assertEqual(t.pool.available, 1)
        t.assertEqual(len(t.pool), 1)

    def test_handleReportStatus(t):
        t.pool.add(t.worker1)
        t.pool.add(t.worker2)

        t.pool.handleReportStatus(event=None)

        t.worker1.remote.callRemote.assert_called_with("reportStatus")
        t.worker2.remote.callRemote.assert_called_with("reportStatus")


class WorkerAvailabilityQueueTest(TestCase):
    """Test the WorkerAvailabilityQueue class."""

    def setUp(t):
        t.queue = WorkerAvailabilityQueue()

    def test_initial_state(t):
        q = WorkerAvailabilityQueue()
        t.assertEqual(0, len(q))
        t.assertTrue(hasattr(q, "pop"))

    def test_add(t):
        value = 10
        t.queue.add(value)
        t.assertEqual(1, len(t.queue))

    def test_add_and_pop(t):
        value = 10
        t.queue.add(value)
        dfr = t.queue.pop()
        t.assertEqual(dfr.result, value)

    def test_pop_empty(t):
        dfr = t.queue.pop()
        t.assertFalse(dfr.called)

    def test_deferred_pop(t):
        dfr = t.queue.pop()
        value = 10
        t.queue.add(value)
        t.assertTrue(dfr.called)
        t.assertEqual(dfr.result, value)

    def test_discard(t):
        value = 10
        t.queue.add(value)
        t.queue.discard(value)
        t.assertEqual(0, len(t.queue))

    def test_discard_empty(t):
        value = 10
        t.queue.discard(value)
        t.assertEqual(0, len(t.queue))
