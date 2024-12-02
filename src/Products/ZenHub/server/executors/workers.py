##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time

from functools import partial

import attr

from attr.validators import instance_of
from twisted.internet import defer
from twisted.internet.task import deferLater, LoopingCall
from twisted.spread import pb
from zope.event import notify

from Products.ZenHub.errors import RemoteException

from ..events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)
from ..priority import (
    ModelingPaused,
    PrioritySelection,
    ServiceCallPriority,
    servicecall_priority_map,
)
from ..service import ServiceCall
from ..worklist import ZenHubWorklist
from ..utils import getLogger

_RemoteErrors = (RemoteException, pb.RemoteError)


class WorkerPoolExecutor(object):
    """An executor that executes service calls using remote workers."""

    @classmethod
    def create(cls, name, config, pool):
        """Return a new executor instance.

        :param str name: The executor's name
        :param IHubServerConfig config: Configuration data
        :param WorkerPool pool: Where the zenhubworker references live
        :return: A new WorkerPoolExecutor instance.
        """
        if config is None:
            raise ValueError("Invalid value for 'config': None")
        if pool is None:
            raise ValueError("Invalid value for 'pool': None")
        modeling_paused = ModelingPaused(
            config.priorities["modeling"],
            config.modeling_pause_timeout,
        )
        selection = PrioritySelection(
            ServiceCallPriority, exclude=modeling_paused
        )
        worklist = ZenHubWorklist(selection)
        return cls(name, worklist, pool, max_retries=config.task_max_retries)

    def __init__(self, name, worklist, pool, max_retries=3):
        """
        Initialize a WorkerPoolExecutor instance.

        @type name: str
        @type worklist: WorkList
        @type pool: WorkerPool
        """
        self._name = name
        self._worklist = worklist
        self._pool = pool
        self._max_retries = max_retries
        self._log = getLogger(self)
        self._scheduler = None
        self._loop = None
        self._loopd = None

    @property
    def name(self):
        """Return the name of this executor."""
        return self._name

    @property
    def pool(self):
        """Return the pool of workers available to this executor."""
        return self._pool

    @property
    def worklist(self):
        """Return the worklist of tasks this executor will execute."""
        return self._worklist

    @property
    def scheduler(self):
        """Return the scheduler that will dispatch the tasks to the workers."""
        return self._scheduler

    @property
    def running(self):
        """Return True if the executor is running."""
        if self._loop is None:
            return False
        return self._loop.running

    def start(self, reactor):
        """Start the executor."""
        self._scheduler = Scheduler(
            reactor, self._name, self._worklist, self._pool
        )
        self._loop = LoopingCall(self._scheduler)
        self._loopd = self._loop.start(0)
        self._log.info("started scheduler  worklist=%s", self._name)

    def stop(self):
        if self._loop is None:
            return
        self._loop.stop()
        self._loop = self._loopd = self._scheduler = None

    def submit(self, call):
        """Submit a ServiceCall for execution.

        Returns a deferred that will fire when execution completes.
        """
        if self._scheduler is None:
            return defer.fail(pb.Error("ZenHub not ready."))
        task = ServiceCallTask(
            worklist=self._name, call=call, max_retries=self._max_retries
        )
        task.mark_received()
        self._log.info(
            "received task  collector=%s service=%s method=%s id=%s",
            task.call.monitor,
            task.call.service,
            task.call.method,
            task.call.id.hex,
        )
        notify(EventBuilder.received(task))
        self._worklist.push(task.priority, task)
        return task.deferred

    def __repr__(self):
        return "<{0.__class__.__name__} '{1}'>".format(self, self._name)


class Scheduler(object):
    """
    Schedule tasks for execution.
    """

    def __init__(self, reactor, name, worklist, pool):
        self.reactor = reactor
        self.name = name
        self.worklist = worklist
        self.workers = pool
        self.log = getLogger(self)

    @defer.inlineCallbacks
    def __call__(self):
        """
        Schedule tasks for execution by workers.
        """
        task = None
        worker = None
        try:
            # Retrieve a task from the work queue
            task = yield self.worklist.pop()

            # Retrieve a worker to execute the task.
            worker = yield self.workers.hire()
            self.log.info(
                "hired worker for task  "
                "worker=%s collector=%s service=%s method=%s id=%s",
                worker.name,
                task.call.monitor,
                task.call.service,
                task.call.method,
                task.call.id,
            )

            # Schedule the worker to execute the task
            dispatcher = TaskDispatcher(worker, task)
            deferLater(self.reactor, 0, dispatcher).addBoth(
                partial(self._task_done, worker, task)
            )
        except Exception:
            self.log.exception("unexpected failure  worklist=%s", self.name)
            if task and task.retryable:
                self.worklist.pushfront(task.priority, task)
            if worker:
                self.workers.ready(worker)

    def _task_done(self, worker, task, *args):
        if task.retryable:
            self.worklist.pushfront(task.priority, task)
            self.log.info(
                "enqueued task for retry  "
                "collector=%s service=%s method=%s id=%s",
                task.call.monitor,
                task.call.service,
                task.call.method,
                task.call.id.hex,
            )
        self.workers.ready(worker)


class TaskDispatcher(object):
    """
    Execute (dispatch) a task to worker and handle the result.
    """

    def __init__(self, worker, task):
        """
        Initialize a TaskDispatcher instance.

        @param worker: The worker to execute the task
        @type worker: WorkerRef
        @param task: The task to be executed by the worker
        @type task: ServiceCallTask
        """
        self.worker = worker
        self.task = task
        self.log = getLogger(self)

    @defer.inlineCallbacks
    def __call__(self):
        """
        Execute the task using the worker.
        """
        status = result = None
        try:
            # Prepare to execute the task.
            self.task.mark_started(self.worker.name)
            if self.task.attempt == 1:
                _log_initial_attempt(self.task, self.log)
            else:
                _log_subsequent_attempts(self.task, self.log)
            notify(EventBuilder.started(self.task))

            # Execute the task
            result = yield self.worker.run(self.task.call)

            # Mark the task execution as successful
            self.task.mark_success(result)
            _log_completed("success", self.task, self.log)
            status = "result"
        except (RemoteException, pb.RemoteError) as ex:
            # These are unretryable errors that originate from the service
            # and are propagated directly back to the submitter.
            self.task.mark_failure(ex)
            _log_completed("failed", self.task, self.log)
            status, result = "error", ex
        except pb.PBConnectionLost as ex:
            # Lost connection to the worker; not a failure.
            self.log.warn(
                "worker no longer accepting tasks  worker=%s",
                self.worker.name,
            )
            if self.task.retryable:
                self.task.mark_retry()
                _log_retry(self.task, ex, self.log)
                status, result = "retry", ex
            else:
                self.log.warn(
                    "retries exhausted  "
                    "collector=%s service=%s method=%s id=%s",
                    self.task.call.monitor,
                    self.task.call.service,
                    self.task.call.method,
                    self.task.call.id.hex,
                )
                self.task.mark_failure(ex)
                _log_completed("failed", self.task, self.log)
                status, result = "error", ex
        except Exception as ex:
            # 'catch-all' error handler and tasks are not retryable.
            self.task.mark_failure(_to_internal_error(ex))
            _log_completed("failed", self.task, self.log)
            status, result = "error", ex
            self.log.exception(
                "unexpected failure  "
                "worklist=%s collector=%s service=%s method=%s id=%s",
                self.task.worklist,
                self.task.call.monitor,
                self.task.call.service,
                self.task.call.method,
                self.task.call.id.hex,
            )
        finally:
            notify(EventBuilder.completed(self.task, status, result))


def _to_internal_error(exception):
    return pb.Error(
        ("Internal ZenHub error: ({0.__class__.__name__}) {0}")
        .format(exception)
        .strip()
    )


class EventBuilder(object):
    @staticmethod
    def received(task):
        """Return a ServiceCallReceived object."""
        data = dict(task.event_data)
        data["timestamp"] = task.received_tm
        return ServiceCallReceived(**data)

    @staticmethod
    def started(task):
        """Return a ServiceCallStarted object."""
        data = dict(task.event_data)
        data.update({"timestamp": task.started_tm, "attempts": task.attempt})
        return ServiceCallStarted(**data)

    @staticmethod
    def completed(task, key, value):
        """Return a ServiceCallCompleted object."""
        data = dict(task.event_data)
        data.update(
            {
                "timestamp": task.completed_tm,
                "attempts": task.attempt,
                key: value,
            }
        )
        return ServiceCallCompleted(**data)


@attr.s(slots=True)
class ServiceCallTask(object):
    """Wraps a ServiceCall to track for use with WorkerPoolExecutor."""

    call = attr.ib(validator=instance_of(ServiceCall))
    worklist = attr.ib(converter=str)
    max_retries = attr.ib(converter=int)

    deferred = attr.ib(factory=defer.Deferred)

    attempt = attr.ib(default=0)
    received_tm = attr.ib(default=None)
    started_tm = attr.ib(default=None)
    completed_tm = attr.ib(default=None)
    worker_name = attr.ib(default=None)

    # These attributes are initialized in __attrs_post_init__.
    desc = attr.ib(init=False)
    priority = attr.ib(init=False)
    event_data = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.desc = "%s:%s.%s" % (
            self.call.monitor,
            self.call.service,
            self.call.method,
        )
        self.priority = servicecall_priority_map.get(
            (self.call.service, self.call.method),
        )
        self.event_data = attr.asdict(self.call)
        self.event_data.update(
            {
                "queue": self.worklist,
                "priority": self.priority,
            }
        )

    @property
    def retryable(self):
        """
        Return True if the task can be re-executed.
        """
        if self.deferred.called:
            return False
        return self.attempt <= self.max_retries

    def mark_received(self):
        """
        Update the task's state to indicate task acceptance.
        """
        self.received_tm = time.time()

    def mark_started(self, worker_name):
        """
        Update the task's state to indicate the task's execution.
        """
        self.attempt += 1
        self.started_tm = time.time()
        self.worker_name = worker_name
        self.event_data["worker"] = worker_name  # needed for completed event

    def mark_success(self, result):
        """
        Update the task's state to indicate the task's successful completion.
        """
        self.completed_tm = time.time()
        self.deferred.callback(result)

    def mark_failure(self, error):
        """
        Update the task's state to indicate the task's failed completion.
        """
        self.completed_tm = time.time()
        self.deferred.errback(error)

    def mark_retry(self):
        """
        Update the task's state to indicate the task's incomplete execution.
        """
        self.completed_tm = time.time()


def _log_retry(task, error, log):
    elapsed = task.completed_tm - task.started_tm
    log.info(
        "failed to complete task  collector=%s service=%s method=%s "
        "id=%s worker=%s duration=%0.2f error=%s",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        elapsed,
        error,
    )


def _log_initial_attempt(task, log):
    waited = task.started_tm - task.received_tm
    log.info(
        "begin task  "
        "collector=%s service=%s method=%s id=%s worker=%s waited=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        waited,
    )


def _log_subsequent_attempts(task, log):
    waited = task.started_tm - task.completed_tm
    log.info(
        "retry task  collector=%s service=%s method=%s id=%s "
        "worker=%s attempt=%s waited=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        task.attempt,
        waited,
    )


def _log_completed(status, task, log):
    elapsed = task.completed_tm - task.started_tm
    lifetime = task.completed_tm - task.received_tm
    log.info(
        "completed task  collector=%s service=%s method=%s id=%s "
        "worker=%s status=%s duration=%0.2f lifetime=%0.2f",
        task.call.monitor,
        task.call.service,
        task.call.method,
        task.call.id.hex,
        task.worker_name,
        status,
        elapsed,
        lifetime,
    )
