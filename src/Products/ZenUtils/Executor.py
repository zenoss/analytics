##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import uuid

from functools import partial

from twisted.internet import defer, error, reactor
from twisted.internet.task import LoopingCall

log = logging.getLogger("zen.executor")


def makeExecutor(queue=None, limit=0, log=log, startnow=True):
    """
    Return a new task executor.

    A limit of zero implies no limit.

    If startnow is False, then the `start` method must be called on the
    returned executor to start the executor running.

    :param name: Name of the executor
    :type name: str
    :param queue: A queue-like object for storing tasks
    :type queue: defer.DeferredQueue() or equivalent
    :param limit: The maximum number of concurrent tasks
    :type limit: int
    :param log: The log object
    :type log: logging.Logger
    :param startnow: If True, start the executor immediately (default True).
    :type startnow: boolean
    :rtype: AsyncExecutor
    """
    if queue is None:
        queue = defer.DeferredQueue()
    tokens = DynamicDeferredSemaphore(limit)
    executor = AsyncExecutor(queue, tokens, log)
    if startnow:
        executor.start(reactor)
    return executor


class AsyncExecutor(object):
    """Executes callables asynchronously.

    @ivar limit: The maximum number number of concurrently executing tasks.
    @type limit: int

    @ivar started: Indicates whether the executor is running
    @type started: boolean

    @ivar running: The count of tasks currently executing.
    @type running: int

    @ivar queued: The count of tasks waiting to execute.
    @type queued: int
    """

    def __init__(self, workqueue, tokens, log):
        """Initialize an AsyncExecutor instance.

        @param workqueue: Uses this queue to store tasks prior to execution.
        @type workqueue: DeferredQueue

        @param tokens: A semaphore used to limit the number of concurrently
            running tasks.
        @type tokens: DynamicDeferredSemaphore

        @param log: The class will use a child logger of the given logger,
            e.g. self.log = log.getChild(type(self).__name__.lower())
        @type log: logging.Logger
        """
        self._id = "%x" % uuid.uuid4().time
        self._queue = workqueue
        self._tokens = tokens
        self._loop = LoopingCall(self.dispatch)
        self._log = log.getChild(self.__class__.__name__.lower())

        self._tasks_running = 0
        self._reactor = None
        self._loopd = None

    def start(self, scheduler):
        """Start scheduling tasks for execution.

        @param scheduler: The scheduler to run the tasks asynchronously.
        @type scheduler: IReactorTime
        """
        if self._loopd and self._loop.running:
            return
        self._reactor = scheduler
        self._loopd = self._loop.start(0)
        self._log.debug(
            "Started executor  executor=%s concurrency-limit=%s",
            self._id, self._tokens.limit,
        )

    def stop(self):
        if self._loopd is not None and not self._loop.running:
            return
        self._loop.stop()
        self._loopd = None
        self._log.debug("Stopped executor loop  executor=%s", self._id)
        # Add a final task to ensure the _execute function can exit.
        if len(self._queue.pending) == 0:
            self._queue.put(
                ExecutorTask(
                    defer.Deferred(), _shutdown_executor, None, self._log,
                ),
            )

    @property
    def started(self):
        return self._loop.running

    @property
    def limit(self):
        return self._tokens.limit

    @limit.setter
    def limit(self, limit):
        self._tokens.limit = limit

    @property
    def running(self):
        return self._tasks_running

    @property
    def queued(self):
        return len(self._queue.pending)

    def submit(self, call, timeout=None, label=""):
        """Submit a callable to run asynchronously.

        :param call: A callable to be executed
        :type call: callable
        :param timeout: how long a task can run before timeout?
        :type timeout: float
        :param label: A optional value to apply to a task.  This value can
            be used to associate related tasks.
        :type label: str

        :return: A Deferred that returns the return value of the callable
            if it does not raise an exception.  If the callable raises an
            exception, the Deferred returns the exception.
        """
        d = defer.Deferred()
        task = ExecutorTask(d, call, timeout, self._log, label)
        self._log.debug(
            "Received task  executor=%s task-id=%s label=%s",
            self._id, task.id, task.label,
        )
        self._queue.put(task)
        return d

    @defer.inlineCallbacks
    def dispatch(self):
        # Schedules tasks for execution.
        token = None
        try:
            # Retrieve a concurrency token.
            # acquire() blocks when there are no tokens left
            self._log.debug("Waiting for a token  executor=%s", self._id)
            token = yield self._tokens.acquire()

            # Retrieve a task
            # get() blocks when there are no tasks in the queue.
            self._log.debug("Waiting for a task  executor=%s", self._id)
            task = yield self._queue.get()

            # Update the number of tasks scheduled for execution.
            self._tasks_running += 1

            # Schedule the task to run at the next available moment.
            self._log.debug(
                "Scheduled task to run  executor=%s task-id=%s label=%s",
                self._id, task.id, task.label,
            )
            self._reactor.callLater(0, self.execute, task)
        except Exception:
            self._log.exception("Unexpected failure  executor=%s", self._id)
            if token:
                token.cancel()

    @defer.inlineCallbacks
    def execute(self, task):
        self._log.debug(
            "Running task  executor=%s task-id=%s label=%s",
            self._id, task.id, task.label,
        )
        try:
            # Wait for the task to complete.
            result = yield task(self._reactor)
            task.finished(result)
        except _ShutdownException:
            self._log.debug("Executor has stopped  executor=%s", self._id)
        except (error.TimeoutError, defer.TimeoutError) as ex:
            self._log.error(
                "Task timed out  executor=%s task-id=%s label=%s",
                self._id, task.id, task.label,
            )
            task.error(ex)
        except defer.CancelledError as ex:
            self._log.debug(
                "Task cancelled (probably due to a connection timeout)  "
                "executor=%s task-id=%s label=%s",
                self._id, task.id, task.label,
            )
            task.error(ex)
        except Exception as ex:
            message = "Bad task  executor=%s task-id=%s label=%s"
            params = (self._id, task.id, task.label)
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.exception(message, *params)
            else:
                self._log.error(message + " error=%s", *(params + (ex,)))
            task.error(ex)
        finally:
            self._tasks_running -= 1
            self._tokens.release()
            self._log.debug(
                "Finished running task  executor=%s task-id=%s label=%s",
                self._id, task.id, task.label,
            )


class TwistedExecutor(AsyncExecutor):
    """Executes callables asynchronously.

    The number of callables that can be executed concurrently can be limited
    by passing in a positive integer for the maxParrallel parameter of the
    class's initializer.  By default, there is no limit.
    """

    def __init__(self, maxParrallel=None, startnow=True):
        """
        @param maxParrallel: the maximum number of tasks that can run
            at a time.
        @type maxParallel: int

        @param startnow: Set True to start the executor immediately.
        @type startnow: boolean
        """
        queue = defer.DeferredQueue()
        limit = maxParrallel if maxParrallel is not None else 0
        tokens = DynamicDeferredSemaphore(limit)
        super(TwistedExecutor, self).__init__(queue, tokens, log)
        if startnow:
            self.start(reactor)

    def getMax(self):
        return self.limit

    def setMax(self, limit):
        self.limit = limit


class ExecutorTask(object):
    """Used by AsyncExecutor to wrap callables for execution.

    @ivar deferred: Fires when the call is complete, errors, or times out.
    @ivar timeout: Number of seconds before timeout.  None means no timeout.
    @ivar call: The callable called when the task is invoked.
    """

    def __init__(self, deferred, call, timeout, log, label=""):
        self.id = "%x" % uuid.uuid4().time
        self.deferred = deferred
        self.timeout = timeout
        self.call = call
        self.label = label
        self._log = log
        self._ontimeout = None

    def __call__(self, reactor):
        d = defer.maybeDeferred(self.call)
        if self.timeout:
            self._log.debug(
                "Setting timeout  task-id=%s label=%s duration=%s",
                self.id, self.label, self.timeout,
            )
            self._ontimeout = defer.Deferred()
            timeout_handler = partial(self._timeout, d)
            self._ontimeout.addTimeout(self.timeout, reactor, timeout_handler)
            # Add a do-nothing errback handler for when the deferred is
            # cancelled before time has elapsed.
            self._ontimeout.addErrback(lambda x: None)
        else:
            self._log.debug(
                "No timeout set  task-id=%s label=%s", self.id, self.label,
            )
        return d

    def finished(self, result):
        if self._ontimeout:
            self._ontimeout.cancel()
        if not self.deferred.called:
            self._log.debug(
                "Setting callback  task-id=%s label=%s result=%r",
                self.id, self.label, result,
            )
            self.deferred.callback(result)
        else:
            self._log.debug(
                "Result ignored  task-id=%s label=%s reason=timeout",
                self.id, self.label,
            )

    def error(self, ex):
        if self._ontimeout:
            self._ontimeout.cancel()
        if isinstance(ex, _ShutdownException):
            return
        if not self.deferred.called:
            self.deferred.errback(ex)
        else:
            self._log.debug(
                "Failure ignored  task-id=%s label=%s reason=timeout",
                self.id, self.label,
            )

    def _timeout(self, calld, failure, timeout):
        # calld is the deferred returned by __call__.
        self._log.debug(
            "Task timed out  task-id=%s label=%s", self.id, self.label,
        )
        error = defer.TimeoutError("timeout")
        calld.errback(error)
        self.deferred.errback(error)
        self._ontimeout = None

    def __repr__(self):
        return (
            "<{0.__module__}.{0.__name__} id={1} label={2}>"
        ).format(type(self), self.id, self.label)


class _ShutdownException(Exception):
    pass


def _shutdown_executor():
    raise _ShutdownException()


class DynamicDeferredSemaphore(object):
    """A semaphore that supports runtime adjustments to its size.

    Setting the DynamicDeferredSemaphore to a zero limit effectively
    creates a semaphore with no limit.

    @ivar limit: The total number of tokens available for acquisition.
    @type limit: int

    @ivar tokens: The number of tokens available for acquisition.
    @type tokens: int
    """

    def __init__(self, limit):
        """Initialize a DynamicDeferredSemaphore instance.

        @param limit: total number of availale tokens.
        @type tokens: int
        """
        if limit < 0:
            raise ValueError("Cannot set the limit to a negative value")
        self._acquired = 0
        self._limit = limit
        self._waiting = []

    @property
    def tokens(self):
        return max(0, self._limit - self._acquired)

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, limit):
        """Update the total number of tokens available for acquisition.

        Reducing the limit does not cancel acquired tokens.

        Increasing the limit will immediately fire pending acquisitions.
        Reducing the limit to zero will also fire pending acquisitions.
        """
        if limit < 0:
            raise ValueError("Cannot set the limit to a negative value")
        self._limit = limit
        if self._limit == 0:
            while self._waiting:
                self._acquired += 1
                self._waiting.pop(0).callback(self)
        else:
            while self._waiting and self._acquired < self._limit:
                self._acquired += 1
                self._waiting.pop(0).callback(self)

    def acquire(self):
        """Acquire a token.

        @return: A Deferred which fires on token acquisition.
        """
        if self._limit == 0 or self._acquired < self._limit:
            self._acquired += 1
            return defer.succeed(self)

        d = defer.Deferred(canceller=self._cancelAcquire)
        self._waiting.append(d)
        d.addErrback(self._ignoreCancelError)
        return d

    def release(self):
        """Release a token.

        Should be called whoever did the acquire() when the shared resource
        is free.
        """
        self._acquired = max(0, self._acquired - 1)
        if self._waiting and self._acquired < self._limit:
            self._acquired += 1
            d = self._waiting.pop(0)
            d.callback(self)

    def _cancelAcquire(self, d):
        if d in self._waiting:
            self._waiting.remove(d)

    def _ignoreCancelError(self, failure):
        failure.trap(defer.CancelledError)
