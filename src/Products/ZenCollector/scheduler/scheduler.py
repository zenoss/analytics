##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging
import random
import time

from collections import Sequence

from twisted.internet import defer, reactor, task
from twisted.python.failure import Failure
from zope.interface import implementer

from Products.ZenUtils.Executor import TwistedExecutor

from ..cyberark import get_cyberark
from ..interfaces import IScheduler, IPausingScheduledTask
from ..tasks import TaskStates

from .statistics import StateStatistics, TaskStatistics
from .task import CallableTaskFactory

log = logging.getLogger("zen.collector.scheduler")


@implementer(IScheduler)
class TaskScheduler(object):
    """
    A simple interval-based scheduler that makes use of the Twisted framework's
    LoopingCall construct.
    """

    CLEANUP_TASKS_INTERVAL = 10  # seconds
    ATTEMPTS = 3

    @classmethod
    def make(cls, factory=None, executor=None):
        factory = factory if factory is not None else CallableTaskFactory()
        executor = executor if executor is not None else TwistedExecutor(1)
        return cls(factory, executor)

    def __init__(self, factory, executor):
        self._loopingCalls = {}
        self._tasks = {}
        self._taskCallback = {}
        self._taskStats = {}
        self._displaycounts = ()
        self._shuttingDown = False

        self._factory = factory
        self._executor = executor

        # create a cleanup task that will periodically sweep the
        # cleanup dictionary for tasks that need to be cleaned
        self._tasksToCleanup = {}
        self._cleanupTask = task.LoopingCall(self._cleanupTasks)
        self._cleanupTask.start(TaskScheduler.CLEANUP_TASKS_INTERVAL)

        self.cyberark = get_cyberark()

        # Ensure that we can cleanly shutdown all of our tasks
        reactor.addSystemEventTrigger(
            "before", "shutdown", self.shutdown, "before"
        )
        reactor.addSystemEventTrigger(
            "during", "shutdown", self.shutdown, "during"
        )
        reactor.addSystemEventTrigger(
            "after", "shutdown", self.shutdown, "after"
        )

    @property
    def executor(self):
        return self._executor

    @property
    def maxTasks(self):
        return self._executor.limit

    @maxTasks.setter
    def maxTasks(self, value):
        self._executor.limit = value

    def __contains__(self, task):
        """
        Returns True if the task has been added to the scheduler.  Otherwise
        False is returned.
        """
        # If task has no 'name' attribute, assume the task name was passed in.
        name = getattr(task, "name", task)
        return name in self._tasks

    def addTask(self, newTask, callback=None, now=False):
        """
        Add a new IScheduledTask object for the scheduler to run.

        @param newTask the task to schedule
        @type newTask IScheduledTask
        @param callback A callable invoked every time the task completes
        @type callback callable
        @param now Set True to run the task now
        @type now boolean
        """
        name = newTask.name
        if name in self._tasks:
            raise ValueError("Task with same name already exists: %s" % name)
        callableTask = self._factory.getCallableTask(newTask, self)
        loopingCall = task.LoopingCall(callableTask)
        self._loopingCalls[name] = loopingCall
        self._tasks[name] = callableTask
        self._taskCallback[name] = callback
        self.taskAdded(callableTask)
        startDelay = getattr(newTask, "startDelay", None)
        if startDelay is None:
            startDelay = 0 if now else self._getStartDelay(newTask)
        reactor.callLater(startDelay, self._startTask, newTask, startDelay)

        # just in case someone does not implement scheduled, lets be careful
        scheduled = getattr(newTask, "scheduled", lambda x: None)
        scheduled(self)
        log.debug(
            "added new task  name=%s config-id=%s interval=%s start-delay=%s",
            newTask.name,
            newTask.configId,
            newTask.interval,
            startDelay,
        )

    def shutdown(self, phase):
        """
        The reactor shutdown has three phases for event types:

            before - tasks can shut down safely at this time with access to
                all services (eg EventService, their own services)
            during - EventService and other services are gone before this
                starts
            after  - not a lot left -- be careful

        Tasks that have the attribute 'stopPhase' can set the state for which
        they should be run, otherwise they will be shut down in the 'before'
        phase.

        Tasks that have the attribute 'stopOrder' can set the order in which
        they are shut down (lowest first).  A stopOrder of 0 (zero) is
        assumed for tasks which do not declare a stopOrder.

        Returns a list of deferreds to wait on.
        """
        self._shuttingDown = True
        doomedTasks = []
        stopQ = {}
        log.debug("In shutdown stage %s", phase)
        for taskName, taskWrapper in self._tasks.iteritems():
            task = taskWrapper.task
            stopPhase = getattr(task, "stopPhase", "before")
            if (
                stopPhase in ("before", "after", "during")
                and stopPhase != phase
            ):
                continue
            stopOrder = getattr(task, "stopOrder", 0)
            queue = stopQ.setdefault(stopOrder, [])
            queue.append((taskName, taskWrapper))

        for stopOrder in sorted(stopQ):
            for taskName, taskWrapper in stopQ[stopOrder]:
                loopTask = self._loopingCalls[taskName]
                if loopTask.running:
                    log.debug("Stopping running task %s", taskName)
                    loopTask.stop()
                log.debug("Removing task %s", taskName)
                doomedTasks.append(taskName)
                self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            self._tasksToCleanup[taskName] = self._tasks[taskName].task

            del self._loopingCalls[taskName]
            del self._tasks[taskName]
            del self._taskStats[taskName]

        cleanupList = self._cleanupTasks()
        return defer.DeferredList(cleanupList)

    def _startTask(self, task, delayed, attempts=0):
        # If there's no LoopingCall or the LoopingCall is running,
        # then there's nothing to do so return
        loopingCall = self._loopingCalls.get(task.name)
        if loopingCall is None or loopingCall.running:
            return

        if task.name in self._tasksToCleanup:
            delay = random.randint(0, int(task.interval / 2))  # noqa: S311
            delayed = delayed + delay
            if attempts > TaskScheduler.ATTEMPTS:
                del self._tasksToCleanup[task.name]
                log.warn(
                    "exceeded max start attempts  name=%s config-id=%s",
                    task.name,
                    task.configId,
                )
                attempts = 0
            attempts += 1
            log.debug(
                "waiting for cleanup  name=%s config-id=%s "
                "current-delay=%s delayed-so-far=%s attempts=%s",
                task.name,
                task.configId,
                delay,
                delayed,
                attempts,
            )
            reactor.callLater(delay, self._startTask, task, delayed, attempts)
        else:
            d = loopingCall.start(task.interval)
            d.addBoth(self._ltCallback, task.name)
            log.debug(
                "started task  name=%s config-id=%s interval=%s "
                "delayed=%s attempts=%s",
                task.name,
                task.configId,
                task.interval,
                delayed,
                attempts,
            )

    def _ltCallback(self, result, task_name):
        """last call back in the chain, if it gets called as an errBack
        the looping will stop - shouldn't be called since CallableTask
        doesn't return a deferred, here for sanity and debug"""
        if task_name in self._loopingCalls:
            log.debug("task finished  name=%s result=%s", task_name, result)
        if isinstance(result, Failure):
            log.warn(
                "Failure in looping call, will not reschedule %s", task_name
            )
            log.error("%s", result)

    def _getStartDelay(self, task):
        """
        amount of time to delay the start of a task. Prevents bunching up of
        task execution when a large amount of tasks are scheduled at the same
        time.
        """
        # simple delay of random number between 0 and half the task interval
        delay = random.randint(0, int(task.interval / 2))  # noqa: S311
        return delay

    def taskAdded(self, taskWrapper):
        """
        Called whenever the scheduler adds a task.
        """
        task = taskWrapper.task

        # watch the task's attribute changes
        task.attachAttributeObserver("state", self._taskStateChangeListener)
        task.attachAttributeObserver(
            "interval", self._taskIntervalChangeListener
        )

        # create the statistics data for this task
        self._taskStats[task.name] = TaskStatistics(task)
        taskWrapper.taskStats = self._taskStats[task.name]

    def taskRemoved(self, taskWrapper):
        """
        Called whenever the scheduler removes a task.
        """
        task = taskWrapper.task
        task.detachAttributeObserver("state", self._taskStateChangeListener)
        task.detachAttributeObserver(
            "interval", self._taskIntervalChangeListener
        )

    def taskPaused(self, taskWrapper):
        """
        Called whenever the scheduler pauses a task.
        """
        if IPausingScheduledTask.providedBy(taskWrapper.task):
            taskWrapper.task.pause()

    def taskResumed(self, taskWrapper):
        """
        Called whenever the scheduler resumes a task.
        """
        if IPausingScheduledTask.providedBy(taskWrapper.task):
            taskWrapper.task.resume()

    def getTasksForConfig(self, configId):
        """
        Get all tasks associated with the specified identifier.
        """
        tasks = []
        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            if task.configId == configId:
                tasks.append(task)
        return tasks

    def getNextExpectedRun(self, taskName):
        """
        Get the next expected execution time for given task.
        """
        loopingCall = self._loopingCalls.get(taskName, None)
        if loopingCall:
            return getattr(loopingCall, "_expectNextCallAt", None)

    def setNextExpectedRun(self, taskName, taskInterval):
        """
        Set the next expected execution time for given task.
        """
        loopingCall = self._loopingCalls.get(taskName, None)
        if loopingCall:
            loopingCall._expectNextCallAt = time.time() + taskInterval
            log.debug(
                "Next expected run %s has been set for task %s",
                loopingCall._expectNextCallAt,
                taskName,
            )

    def removeTasks(self, taskNames):
        # type: (Self, Sequence[str]) -> None
        """
        Remove tasks
        """
        if not isinstance(taskNames, Sequence):
            taskNames = tuple(taskNames)

        doomedTasks = []
        # child ids are any task that are children of the current task being
        # removed
        childIds = []
        for name in taskNames:
            taskWrapper = self._tasks[name]
            task = taskWrapper.task
            subIds = getattr(task, "childIds", None)
            if subIds:
                childIds.extend(subIds)
            if self._loopingCalls[name].running:
                self._loopingCalls[name].stop()
                log.debug(
                    "stopped task  name=%s config-id=%s", name, task.configId
                )
            doomedTasks.append(name)
            self.taskRemoved(taskWrapper)

        for taskName in doomedTasks:
            task = self._tasks[taskName].task
            self._tasksToCleanup[taskName] = task
            del self._loopingCalls[taskName]
            del self._tasks[taskName]
            self._displayTaskStatistics(task)
            del self._taskStats[taskName]
            log.debug(
                "removed task  name=%s config-id=%s", task.name, task.configId
            )

        map(self.removeTasksForConfig, childIds)

    def removeTasksForConfig(self, configId):
        """
        Remove all tasks associated with the specified identifier.

        @paramater configId: the identifier to search for
        @type configId: string
        """
        self.removeTasks(
            tuple(
                name
                for name, wrapper in self._tasks.iteritems()
                if wrapper.task.configId == configId
            )
        )

    def pauseTasksForConfig(self, configId):
        for taskName, taskWrapper in self._tasks.items():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Pausing task %s", taskName)
                taskWrapper.paused = True
                self.taskPaused(taskWrapper)

    def resumeTasksForConfig(self, configId):
        for taskName, taskWrapper in self._tasks.iteritems():
            task = taskWrapper.task
            if task.configId == configId:
                log.debug("Resuming task %s", taskName)
                taskWrapper.paused = False
                self.taskResumed(taskWrapper)

    def taskDone(self, taskName):
        if callable(self._taskCallback[taskName]):
            self._taskCallback[taskName](taskName=taskName)

    def _taskStateChangeListener(
        self, observable, attrName, oldValue, newValue
    ):
        task = observable

        log.debug(
            "Task %s changing state from %s to %s",
            task.name,
            oldValue,
            newValue,
        )

        taskStat = self._taskStats[task.name]
        taskStat.trackStateChange(oldValue, newValue)

    def _taskIntervalChangeListener(
        self, observable, attrName, oldValue, newValue
    ):
        """
        Allows tasks to change their collection interval on the fly
        """
        task = observable
        log.debug(
            "Task %s changing run interval from %s to %s",
            task.name,
            oldValue,
            newValue,
        )
        # TODO: should this be...
        # loopingCall = self._loopingCalls[task.name]
        loopingCall = task._dataService._scheduler._loopingCalls[task.name]
        loopingCall.interval = newValue

    @property
    def missedRuns(self):
        totalMissedRuns = 0
        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]
            totalMissedRuns += taskStats.missedRuns
        return totalMissedRuns

    @property
    def failedRuns(self):
        totalFailedRuns = 0
        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]
            totalFailedRuns += taskStats.failedRuns
        return totalFailedRuns

    @property
    def taskCount(self):
        return len(self._tasks)

    def displayStatistics(self, verbose):
        totalRuns = 0
        totalFailedRuns = 0
        totalMissedRuns = 0
        totalTasks = 0
        stateStats = {}

        for taskWrapper in self._tasks.itervalues():
            task = taskWrapper.task
            taskStats = self._taskStats[task.name]

            totalTasks += 1
            totalRuns += taskStats.totalRuns
            totalFailedRuns += taskStats.failedRuns
            totalMissedRuns += taskStats.missedRuns

            for state, stats in taskStats.states.iteritems():
                if state in stateStats:
                    totalStateStats = stateStats[state]
                else:
                    totalStateStats = StateStatistics(state)
                    stateStats[state] = totalStateStats
                totalStateStats.totalElapsedTime += stats.totalElapsedTime
                totalStateStats.totalElapsedTimeSquared += (
                    stats.totalElapsedTimeSquared
                )
                totalStateStats.totalCalls += stats.totalCalls
                totalStateStats.minElapsedTime = min(
                    totalStateStats.minElapsedTime, stats.minElapsedTime
                )
                totalStateStats.maxElapsedTime = max(
                    totalStateStats.maxElapsedTime, stats.maxElapsedTime
                )

        counts = (
            totalTasks,
            totalRuns,
            totalFailedRuns,
            totalMissedRuns,
            self._executor.queued,
            self._executor.running,
        )
        if self._displaycounts != counts:
            self._displaycounts = counts
            logmethod = log.info
        else:
            logmethod = log.debug
        logmethod(
            "Tasks: %d Successful_Runs: %d Failed_Runs: %d "
            "Missed_Runs: %d Queued_Tasks: %d Running_Tasks: %d ",
            *counts
        )

        if verbose:
            buffer = "Task States Summary:\n"
            buffer = self._displayStateStatistics(buffer, stateStats)

            buffer += "\nTasks:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                buffer += (
                    "%s Current State: %s Successful_Runs: %d "
                    "Failed_Runs: %d Missed_Runs: %d\n"
                    % (
                        task.name,
                        task.state,
                        taskStats.totalRuns,
                        taskStats.failedRuns,
                        taskStats.missedRuns,
                    )
                )

            buffer += "\nDetailed Task States:\n"
            for taskWrapper in self._tasks.itervalues():
                task = taskWrapper.task
                taskStats = self._taskStats[task.name]

                if not taskStats.states:  # Hasn't run yet
                    continue

                buffer = self._displayStateStatistics(
                    buffer, taskStats.states, "%s " % task.name
                )

                if hasattr(task, "displayStatistics"):
                    buffer += task.displayStatistics()

                buffer += "\n"

            log.info("Detailed Scheduler Statistics:\n%s", buffer)

        # TODO: the above logic doesn't print out any stats for the 'current'
        # state... i.e. enter the PAUSED state and wait there an hour, and
        # you'll see no data

        # TODO: should we reset the statistics here, or do it on a periodic
        # interval, like once an hour or day or something?

    def _displayTaskStatistics(self, task):
        verbose = log.isEnabledFor(logging.DEBUG)
        if not verbose:
            return
        taskStats = self._taskStats[task.name]

        buffer = (
            "%s Current State: %s Successful_Runs: %d "
            "Failed_Runs: %d Missed_Runs: %d\n"
            % (
                task.name,
                task.state,
                taskStats.totalRuns,
                taskStats.failedRuns,
                taskStats.missedRuns,
            )
        )

        buffer += "\nDetailed Task States:\n"
        if taskStats.states:  # Hasn't run yet
            buffer = self._displayStateStatistics(
                buffer, taskStats.states, "%s " % task.name
            )

            if hasattr(task, "displayStatistics"):
                buffer += task.displayStatistics()

        buffer += "\n"

        log.info("Detailed Task Statistics:\n%s", buffer)

    def _displayStateStatistics(self, buffer, stateStats, prefix=""):
        for state, stats in stateStats.iteritems():
            buffer += (
                "%sState: %s Total: %d Total Elapsed: %.4f "
                "Min: %.4f Max: %.4f Mean: %.4f StdDev: %.4f\n"
                % (
                    prefix,
                    state,
                    stats.totalCalls,
                    stats.totalElapsedTime,
                    stats.minElapsedTime,
                    stats.maxElapsedTime,
                    stats.mean,
                    stats.stddev,
                )
            )
        return buffer

    def _cleanupTasks(self):
        """
        Periodically cleanup tasks that have been queued up for cleaning.
        """
        # Build a list of the tasks that need to be cleaned up so that there
        # is no issue with concurrent modifications to the _tasksToCleanup
        # dictionary when tasks are quickly cleaned up.
        if self._tasksToCleanup:
            log.debug("tasks to clean %s", self._tasksToCleanup)

        todoList = [
            task
            for task in self._tasksToCleanup.values()
            if self._isTaskCleanable(task)
        ]

        cleanupWaitList = []
        for item in todoList:
            # changing the state of the task will keep the next cleanup run
            # from processing it again
            item.state = TaskStates.STATE_CLEANING
            if self._shuttingDown:
                # let the task know the scheduler is shutting down
                item.state = TaskStates.STATE_SHUTDOWN
            log.debug("Cleanup on task %s %s", item.name, item)
            d = defer.maybeDeferred(item.cleanup)
            d.addBoth(self._cleanupTaskComplete, item)
            cleanupWaitList.append(d)
        return cleanupWaitList

    def _cleanupTaskComplete(self, result, task):
        """
        Twisted callback to remove a task from the cleanup queue once it has
        completed its cleanup work.
        """
        log.debug(
            "Scheduler._cleanupTaskComplete: result=%s task.name=%s",
            result,
            task.name,
        )
        del self._tasksToCleanup[task.name]
        return result

    def _isTaskCleanable(self, task):
        """
        Determines if a task is able to be cleaned up or not.
        """
        return task.state in (
            TaskStates.STATE_IDLE,
            TaskStates.STATE_PAUSED,
            TaskStates.STATE_COMPLETED,
            TaskStates.STATE_CONNECTING,
        )

    def resetStats(self, taskName):
        taskStats = self._taskStats[taskName]
        taskStats.totalRuns = 0
        taskStats.failedRuns = 0
        taskStats.missedRuns = 0


class Scheduler(TaskScheduler):
    """Backward compatibility layer."""

    def __init__(self):
        super(Scheduler, self).__init__(
            CallableTaskFactory(), TwistedExecutor(1)
        )
