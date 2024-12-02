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
import os
import sys

from StringIO import StringIO

from twisted.internet import defer
from twisted.python.failure import Failure

from Products.ZenEvents import Event
from Products.ZenUtils.Utils import dumpCallbacks

from ..interfaces import IScheduledTask
from ..tasks import TaskStates

log = logging.getLogger("zen.collector.scheduler")


class CallableTask(object):
    """
    A CallableTask wraps an IScheduledTask object to make it a callable.
    This allows the scheduler to make use of the Twisted framework's
    LoopingCall construct for simple interval-based scheduling.
    """

    def __init__(self, task, scheduler, executor):
        if not IScheduledTask.providedBy(task):
            raise TypeError("task must provide IScheduledTask")

        self.task = task
        self.task._scheduler = scheduler
        self._scheduler = scheduler
        self._executor = executor
        self.paused = False
        self.taskStats = None

    def __repr__(self):
        return "CallableTask: %s" % getattr(self.task, "name", self.task)

    def running(self):
        """
        Called whenever this task is being run.
        """
        if hasattr(self.task, "missed"):
            self._send_clear_event()
        self.taskStats.totalRuns += 1

    def logTwistedTraceback(self, reason):
        """
        Twisted errBack to record a traceback and log messages
        """
        out = StringIO()
        reason.printTraceback(out)
        # This shouldn't be necessary except for dev code
        log.debug(out.getvalue())
        out.close()

    def finished(self, result):
        """
        Called whenever this task has finished.
        """
        if isinstance(result, Failure):
            self.taskStats.failedRuns += 1
            self.logTwistedTraceback(result)

    def late(self):
        """
        Called whenever this task is late and missed its scheduled run time.
        """
        # some tasks we don't want to consider a missed run.
        if getattr(self.task, "suppress_late", False):
            return
        self._send_warning_event()
        self.taskStats.missedRuns += 1

    def _send_warning_event(self):
        try:
            # send event only for missed runs on devices.
            self.task._eventService.sendEvent(
                {
                    "eventClass": "/Perf/MissedRuns",
                    "component": os.path.basename(sys.argv[0]).replace(
                        ".py", ""
                    ),
                },
                device=self.task._devId,
                summary="Missed run: {}".format(self.task.name),
                message=self._scheduler._displayStateStatistics(
                    "", self.taskStats.states
                ),
                severity=Event.Warning,
                eventKey=self.task.name,
            )
            self.task.missed = True
        except Exception:
            if log.isEnabledFor(logging.DEBUG):
                log.exception("unable to send /Perf/MissedRuns warning event")

    def _send_clear_event(self):
        try:
            self.task._eventService.sendEvent(
                {
                    "eventClass": "/Perf/MissedRuns",
                    "component": os.path.basename(sys.argv[0]).replace(
                        ".py", ""
                    ),
                },
                device=self.task._devId,
                summary="Task `{}` is being run.".format(self.task.name),
                severity=Event.Clear,
                eventKey=self.task.name,
            )
            del self.task.missed
        except Exception:
            if log.isEnabledFor(logging.DEBUG):
                log.exception("unable to send /Perf/MissedRuns clear event")

    def __call__(self):
        if self.task.state is TaskStates.STATE_PAUSED and not self.paused:
            self.task.state = TaskStates.STATE_IDLE
        elif self.paused and self.task.state is not TaskStates.STATE_PAUSED:
            self.task.state = TaskStates.STATE_PAUSED

        self._scheduler.setNextExpectedRun(self.task.name, self.task.interval)

        if self.task.state in [TaskStates.STATE_IDLE, TaskStates.STATE_PAUSED]:
            if not self.paused:
                self.task.state = TaskStates.STATE_QUEUED
                # don't return deferred to looping call.
                # If a deferred is returned to looping call
                # it won't reschedule on error and will only
                # reschedule after the deferred is done. This method
                # should be called regardless of whether or
                # not the task is still running to keep track
                # of "late" tasks
                d = self._executor.submit(self._doCall)

                def _callError(failure):
                    msg = "%s - %s failed %s" % (
                        self.task,
                        self.task.name,
                        failure,
                    )
                    log.debug(msg)
                    # don't return failure to prevent
                    # "Unhandled error in Deferred" message
                    return msg

                # l last error handler in the chain
                d.addErrback(_callError)
        else:
            self._late()
        # don't return a Deferred because we want LoopingCall to keep
        # rescheduling so that we can keep track of late intervals

    def _doCall(self):
        d = defer.maybeDeferred(self._run)
        d.addBoth(self._finished)

        # dump the deferred chain if we're in ludicrous debug mode
        if log.getEffectiveLevel() < logging.DEBUG:
            print("Callback Chain for Task %s" % self.task.name)
            dumpCallbacks(d)
        return d

    def _run(self):
        self.task.state = TaskStates.STATE_RUNNING
        self.running()

        return self.task.doTask()

    def _finished(self, result):
        log.debug("Task %s finished, result: %r", self.task.name, result)

        # Unless the task completed or paused itself, make sure
        # that we always reset the state to IDLE once the task is finished.
        if self.task.state != TaskStates.STATE_COMPLETED:
            self.task.state = TaskStates.STATE_IDLE

        self._scheduler.taskDone(self.task.name)

        self.finished(result)

        if self.task.state == TaskStates.STATE_COMPLETED:
            self._scheduler.removeTasksForConfig(self.task.configId)

        # return result for executor callbacks
        return result

    def _late(self):
        log.debug("Task %s skipped because it was not idle", self.task.name)
        self.late()


class CallableTaskFactory(object):
    """
    A factory that creates instances of CallableTask, allowing it to be
    easily subclassed or replaced in different scheduler implementations.
    """

    def getCallableTask(self, newTask, scheduler):
        return CallableTask(newTask, scheduler, scheduler.executor)
