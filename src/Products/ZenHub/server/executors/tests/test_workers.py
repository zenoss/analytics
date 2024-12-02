##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

from unittest import TestCase

import attr

from mock import (
    ANY,
    MagicMock,
    Mock,
    NonCallableMagicMock,
    patch,
)
from twisted.internet import defer, reactor
from twisted.python.failure import Failure
from twisted.spread import pb

# from Products.ZenHub.errors import RemoteException
from Products.ZenHub.server.config import ModuleObjectConfig
from Products.ZenHub.server.service import ServiceCall
from Products.ZenHub.server.worklist import ZenHubWorklist
from Products.ZenHub.server.workerpool import WorkerPool
from Products.ZenHub.server.utils import subTest

from ..workers import (
    RemoteException,
    Scheduler,
    TaskDispatcher,
    ServiceCallPriority,
    ServiceCallTask,
    WorkerPoolExecutor,
    _to_internal_error,
)

PATH = {"src": "Products.ZenHub.server.executors.workers"}


class WorkerPoolExecutorTest(TestCase):
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.loopingCall_patcher = patch(
            "{src}.LoopingCall".format(**PATH),
            autospec=True,
        )
        t.loopingCall = t.loopingCall_patcher.start()
        t.addCleanup(t.loopingCall_patcher.stop)

        t.notify_patcher = patch(
            "{src}.notify".format(**PATH),
            autospec=True,
        )
        t.notify = t.notify_patcher.start()
        t.addCleanup(t.notify_patcher.stop)

        t.reactor = Mock(spec=reactor)
        t.worklist = NonCallableMagicMock(spec=ZenHubWorklist)
        t.pool = NonCallableMagicMock(spec=WorkerPool)

        t.name = "default"
        t.executor = WorkerPoolExecutor(
            t.name,
            t.worklist,
            t.pool,
        )
        t.logger = t.getLogger(t.executor)

    @patch("{src}.ModelingPaused".format(**PATH), autospec=True)
    @patch("{src}.PrioritySelection".format(**PATH), autospec=True)
    @patch("{src}.ZenHubWorklist".format(**PATH), autospec=True)
    def test_create(t, _zhwlist, _ps, _mp):
        config = MagicMock(spec=ModuleObjectConfig)
        pool = Mock()
        result = WorkerPoolExecutor.create(t.name, config, pool)

        _mp.assert_called_once_with(
            config.priorities["modeling"],
            config.modeling_pause_timeout,
        )
        _ps.assert_called_once_with(
            ServiceCallPriority,
            exclude=_mp.return_value,
        )
        _zhwlist.assert_called_once_with(_ps.return_value)
        t.assertIsInstance(result, WorkerPoolExecutor)
        t.assertEqual(result.name, t.name)
        t.assertIs(result._worklist, _zhwlist.return_value)
        t.assertIs(result._pool, pool)

    def test_create_requires_pool_and_config_args(t):
        cases = {
            "no args": {"config": None, "pool": None},
            "missing 'config'": {"config": None, "pool": Mock()},
            "missing 'pool'": {"config": Mock(), "pool": None},
        }
        for name, params in cases.items():
            with subTest(case=name):
                with t.assertRaises(ValueError):
                    WorkerPoolExecutor.create(t.name, **params)

    def test_initial_state(t):
        t.assertEqual(t.name, t.executor.name)
        t.assertEqual(t.pool, t.executor.pool)
        t.assertEqual(t.worklist, t.executor.worklist)

    def test_start(t):
        t.executor.start(t.reactor)

        t.assertTrue(t.executor.running)
        scheduler = t.executor.scheduler
        t.assertIsInstance(scheduler, Scheduler)
        t.assertIs(scheduler.reactor, t.reactor)
        t.assertEqual(scheduler.name, t.name)
        t.assertEqual(scheduler.workers, t.pool)
        t.assertEqual(scheduler.worklist, t.worklist)

    def test_stop(t):
        t.executor.stop()
        t.assertIsNone(t.executor.scheduler)
        t.assertFalse(t.executor.running)

    def test_stop_after_start(t):
        t.executor.start(t.reactor)
        t.executor.stop()
        t.assertIsNone(t.executor.scheduler)
        t.assertFalse(t.executor.running)

    def test_submit_on_unstarted_executor(t):
        """
        Submit returns a deferred.failure object if the executor is stopped.
        """
        call = Mock(spec=ServiceCall)

        dfr = t.executor.submit(call)
        handler = Mock(name="errback handler")
        dfr.addErrback(handler)  # silence 'unhandled error in deffered'

        f = handler.call_args[0][0]
        t.assertIsInstance(f, Failure)
        t.assertIsInstance(f.value, pb.Error)
        t.assertEqual("ZenHub not ready.", str(f.value))

    def test_submit_on_running_executor(t):
        t.executor.start(t.reactor)

        call = Mock(spec=ServiceCall)

        dfr = t.executor.submit(call)

        t.assertFalse(dfr.called)
        t.notify.assert_called_once_with(ANY)
        t.worklist.push.assert_called_once_with(ANY, ANY)


class SchedulerTest(TestCase):
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.deferLater_patcher = patch(
            "{src}.deferLater".format(**PATH),
            autospec=True,
        )
        t.deferLater = t.deferLater_patcher.start()
        t.addCleanup(t.deferLater_patcher.stop)

        t.taskDispatcher_patcher = patch(
            "{src}.TaskDispatcher".format(**PATH),
            autospec=True,
        )
        t.taskDispatcher = t.taskDispatcher_patcher.start()
        t.addCleanup(t.taskDispatcher_patcher.stop)

        t.reactor = Mock(spec=reactor)
        t.worklist = NonCallableMagicMock(spec=ZenHubWorklist)
        t.pool = NonCallableMagicMock(spec=WorkerPool)
        t.name = "default"

        t.sched = Scheduler(t.reactor, t.name, t.worklist, t.pool)
        t.logger = t.getLogger(t.sched)

    def test_initialized_attributes(t):
        t.assertIs(t.reactor, t.sched.reactor)
        t.assertIs(t.name, t.sched.name)
        t.assertIs(t.worklist, t.sched.worklist)
        t.assertIs(t.pool, t.sched.workers)

    def test_nominal_task_success(t):
        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3

        task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        task.mark_success(True)
        t.worklist.pop.return_value = defer.succeed(task)

        worker = Mock(spec=["name"])
        t.pool.hire.return_value = defer.succeed(worker)

        dispatch_deferred = defer.succeed(None)
        t.deferLater.return_value = dispatch_deferred

        t.sched()

        t.taskDispatcher.assert_called_once_with(worker, task)
        t.assertFalse(t.worklist.pushfront.called)
        t.pool.ready.assert_called_once_with(worker)

    def test_nominal_task_failure(t):
        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3

        task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        task.mark_failure(RuntimeError("boom"))
        t.worklist.pop.return_value = defer.succeed(task)

        worker = Mock(spec=["name"])
        t.pool.hire.return_value = defer.succeed(worker)

        dispatch_deferred = defer.succeed(None)
        t.deferLater.return_value = dispatch_deferred

        t.sched()

        t.taskDispatcher.assert_called_once_with(worker, task)
        t.assertFalse(t.worklist.pushfront.called)
        t.pool.ready.assert_called_once_with(worker)

        # silence 'Unhandled error in Deferred'
        task.deferred.addErrback(lambda x: None)

    def test_task_retry(t):
        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3
        task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        task.mark_retry()
        t.worklist.pop.return_value = defer.succeed(task)

        worker = Mock(spec=["name"])
        t.pool.hire.return_value = defer.succeed(worker)

        dispatch_deferred = defer.succeed(None)
        t.deferLater.return_value = dispatch_deferred

        t.sched()

        t.worklist.pushfront.assert_called_once_with(task.priority, task)
        t.pool.ready.assert_called_once_with(worker)

    def test_worklist_pop_error(t):
        t.worklist.pop.side_effect = RuntimeError("boom")

        t.sched()

        t.assertFalse(t.pool.hire.called)
        t.assertFalse(t.taskDispatcher.called)
        t.assertFalse(t.deferLater.called)
        t.assertFalse(t.pool.ready.called)

    def test_pool_hire_error(t):
        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3
        task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        t.worklist.pop.return_value = defer.succeed(task)

        t.pool.hire.side_effect = RuntimeError("boom")

        t.sched()

        t.assertFalse(t.taskDispatcher.called)
        t.assertFalse(t.deferLater.called)
        t.assertFalse(t.pool.ready.called)

    def test_taskdispatcher_error(t):
        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3
        task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        t.worklist.pop.return_value = defer.succeed(task)

        worker = Mock(spec=["name"])
        t.pool.hire.return_value = defer.succeed(worker)

        dispatch_deferred = defer.succeed(None)
        t.deferLater.return_value = dispatch_deferred

        t.taskDispatcher.side_effect = RuntimeError("boom")

        t.sched()

        t.assertFalse(t.deferLater.called)
        t.worklist.pushfront.assert_called_once_with(task.priority, task)
        t.pool.ready.assert_called_once_with(worker)


class TaskDispatcherTest(TestCase):
    def setUp(t):
        t.getLogger_patcher = patch(
            "{src}.getLogger".format(**PATH),
            autospec=True,
        )
        t.getLogger = t.getLogger_patcher.start()
        t.addCleanup(t.getLogger_patcher.stop)

        t.notify_patcher = patch(
            "{src}.notify".format(**PATH),
            autospec=True,
        )
        t.notify = t.notify_patcher.start()
        t.addCleanup(t.notify_patcher.stop)

        t.worker = Mock(spec=["name", "run"])

        call = MagicMock(spec=ServiceCall)
        worklist_name = "default"
        retries = 3
        t.task = ServiceCallTask(
            call=call, worklist=worklist_name, max_retries=retries
        )
        moment = time.time()
        t.task.received_tm = moment - 5
        t.dispatcher = TaskDispatcher(t.worker, t.task)

    def test_nominal_call_success(t):
        result = {"a": 1}
        t.worker.run.return_value = defer.succeed(result)

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertTrue(t.task.deferred.called)
        t.assertEqual(t.task.deferred.result, result)
        t.assertFalse(t.task.retryable)

    def test_call_with_remoteerror(t):
        mesg = "boom"
        error = pb.RemoteError(RuntimeError, mesg, MagicMock())
        t.worker.run.return_value = defer.fail(error)

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertTrue(t.task.deferred.called)
        t.assertIsInstance(t.task.deferred.result, Failure)
        t.assertEqual(t.task.deferred.result.getErrorMessage(), mesg)
        t.assertFalse(t.task.retryable)

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)

    def test_call_with_remoteexception(t):
        mesg = "boom"
        tb = "Traceback"
        expected_mesg = "{}:\n{}".format(mesg, tb)
        error = RemoteException(mesg, tb)
        t.worker.run.return_value = defer.fail(error)

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertTrue(t.task.deferred.called)
        t.assertIsInstance(t.task.deferred.result, Failure)
        t.assertEqual(t.task.deferred.result.getErrorMessage(), expected_mesg)
        t.assertFalse(t.task.retryable)

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)

    def test_call_with_retryable_connectionlost(t):
        error = pb.PBConnectionLost()
        t.worker.run.return_value = defer.fail(error)

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertTrue(t.task.retryable)

    def test_call_with_unretryable_connectionlost(t):
        error = pb.PBConnectionLost()
        t.worker.run.return_value = defer.fail(error)
        t.task.attempt = t.task.max_retries
        t.task.completed_tm = time.time() + 1

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertFalse(t.task.retryable)
        t.assertTrue(t.task.deferred.called)
        t.assertIsInstance(t.task.deferred.result, Failure)
        t.assertEqual(t.task.deferred.result.getErrorMessage(), "")

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)

    def test_call_with_internal_error(t):
        error = RuntimeError("boom")
        expected_error = _to_internal_error(error)
        t.worker.run.return_value = defer.fail(error)

        t.dispatcher()

        t.assertIsNotNone(t.task.started_tm)
        t.assertIsNotNone(t.task.completed_tm)
        t.assertFalse(t.task.retryable)
        t.assertTrue(t.task.deferred.called)
        t.assertIsInstance(t.task.deferred.result, Failure)
        t.assertEqual(
            t.task.deferred.result.getErrorMessage(), str(expected_error)
        )

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)


class ServiceCallTaskTest(TestCase):
    """Test the ServiceCallTask class."""

    def setUp(t):
        t.worklist = "queue"
        t.monitor = "localhost"
        t.service = "service"
        t.method = "method"
        t.call = ServiceCall(
            monitor=t.monitor,
            service=t.service,
            method=t.method,
            args=[],
            kwargs={},
        )
        t.retries = 4
        t.task = ServiceCallTask(
            worklist=t.worklist, call=t.call, max_retries=t.retries
        )

    def test_worklist_attribute(t):
        t.assertEqual(t.task.worklist, t.worklist)

    def test_max_retries_attribute(t):
        t.assertEqual(t.task.max_retries, t.retries)

    def test_call_attribute(t):
        t.assertIs(t.call, t.task.call)

    def test_deferred_attribute(t):
        t.assertIsInstance(t.task.deferred, defer.Deferred)

    def test_desc_attribute(t):
        expected_desc = "%s:%s.%s" % (t.monitor, t.service, t.method)
        t.assertEqual(expected_desc, t.task.desc)

    def test_initial_attempt_value(t):
        t.assertEqual(0, t.task.attempt)

    def test_priority_attribute(t):
        t.assertEqual(t.task.priority, ServiceCallPriority.OTHER)

    def test_default_timestamps(t):
        t.assertIsNone(t.task.received_tm)
        t.assertIsNone(t.task.started_tm)
        t.assertIsNone(t.task.completed_tm)

    def test_default_worker_name_attribute(t):
        t.assertIsNone(t.task.worker_name)

    def test_default_event_data_attribute(t):
        expected_event_data = attr.asdict(t.call)
        expected_event_data.update(
            {
                "queue": t.worklist,
                "priority": t.task.priority,
            }
        )
        t.assertDictEqual(t.task.event_data, expected_event_data)

    def test_retryable_initially(t):
        t.assertTrue(t.task.retryable)

    def test_retryable_max_reached(t):
        t.task.attempt = t.retries + 1
        t.assertFalse(t.task.retryable)

    def test_retryable_deferred_callback(t):
        t.task.deferred.callback(None)
        t.assertFalse(t.task.retryable)

    def test_retryable_deferred_errback(t):
        t.task.deferred.errback(RuntimeError("boom"))
        t.assertFalse(t.task.retryable)

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_mark_received(t, _time):
        expected_tm = _time.time.return_value
        t.task.mark_received()
        t.assertEqual(expected_tm, t.task.received_tm)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_mark_started(t, _time):
        expected_tm = _time.time.return_value
        worker_name = "default_0"
        t.task.mark_started(worker_name)
        t.assertEqual(expected_tm, t.task.started_tm)
        t.assertEqual(1, t.task.attempt)
        t.assertEqual(worker_name, t.task.worker_name)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_mark_success(t, _time):
        t.task.attempt = 1
        expected_tm = _time.time.return_value
        result = Mock()

        t.task.mark_success(result)

        t.assertFalse(t.task.retryable)
        t.assertEqual(expected_tm, t.task.completed_tm)
        t.assertEqual(1, t.task.attempt)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_mark_failure(t, _time):
        t.task.attempt = 1
        expected_tm = _time.time.return_value
        error = RuntimeError("boom")

        t.task.mark_failure(error)

        t.assertFalse(t.task.retryable)
        t.assertEqual(expected_tm, t.task.completed_tm)
        t.assertEqual(1, t.task.attempt)

        # silence 'Unhandled error in Deferred'
        t.task.deferred.addErrback(lambda x: None)

    @patch("{src}.time".format(**PATH), autospec=True)
    def test_mark_retry(t, _time):
        t.task.attempt = 1
        expected_tm = _time.time.return_value

        t.task.mark_retry()

        t.assertTrue(t.task.retryable)
        t.assertEqual(expected_tm, t.task.completed_tm)
        t.assertEqual(1, t.task.attempt)
