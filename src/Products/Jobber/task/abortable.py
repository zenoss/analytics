##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os
import signal
import sys
import thread
import threading
import time

from celery import states
from celery.app import push_current_task, pop_current_task
from celery.exceptions import Ignore
from celery.contrib.abortable import (
    AbortableAsyncResult,
    AbortableTask,
    ABORTED,
)
from zope.component import getUtility

from Products.ZenUtils.Threading import inject_exception_into_thread

from ..exceptions import JobAborted, TaskAborted
from ..interfaces import IJobStore
from ..utils.log import get_logger

mlog = get_logger("zen.zenjobs.task.abortable")


class AbortableResult(AbortableAsyncResult):
    """The result of an Abortable."""

    def abort(self):
        """Abort the job."""
        jobstore = getUtility(IJobStore, "redis")
        jobstore.update(self.id, status=ABORTED, finished=time.time())
        return super(AbortableResult, self).abort()


class Abortable(AbortableTask):
    """A task that can be aborted."""

    abstract = True
    throws = (TaskAborted,)

    def AsyncResult(self, task_id):
        """Return the accompanying AbortableResult instance."""
        return AbortableResult(task_id, backend=self.backend)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        result = super(Abortable, self).on_failure(
            exc, task_id, args, kwargs, einfo
        )
        # If the exception is TaskAborted, change the status to ABORTED
        # because Celery always marks jobs that raise an exception as FAILURE.
        if isinstance(exc, TaskAborted):
            result = self.AsyncResult(task_id)
            result.backend.store_result(
                task_id, result=exc, status=states.ABORTED, traceback=None
            )
            mlog.debug(
                "On TaskAborted exception, reset the task status to ABORTED",
            )

        return result

    def __call__(self, *args, **kwargs):
        """Execute the task."""
        # Ignore this task if it's already aborted.
        jobstore = getUtility(IJobStore, "redis")
        status = jobstore.getfield(self.request.id, "status")
        # This check may need to be in base.ZenTask instead if it's
        # decided to have un-abortable jobs visible in the Zenoss UI.
        if not status and not self.ignore_result:
            mlog.info("Ignoring deleted job")
            raise Ignore()
        if status == ABORTED:
            log_mesg = "Ignoring aborted job"
            self.log.info(log_mesg)
            mlog.info(log_mesg)
            raise Ignore()

        # Alias the original run to __run
        # Alias _exec to run
        # _exec will call __run
        self.__run, self.run = self.run, self.__exec

        try:
            return super(Abortable, self).__call__(*args, **kwargs)
        finally:
            self.run = self.__run
            del self.__run

    def __exec(self, *args, **kwargs):
        aborter = _TaskAborter(self, thread.get_ident())
        try:
            aborter.start()
            mlog.debug("Started the ABORTED status monitor thread")
            return self.__run(*args, **kwargs)
        except JobAborted:
            aborted_mesg = "Job aborted"
            self.log.warning(aborted_mesg)
            mlog.warning(aborted_mesg)
            # Convert JobAborted into TaskAborted.
            # JobAborted is derived from BaseException and TaskAborted
            # is derviced from Exception.  Raising TaskAborted will result
            # in desired behavior from Celery.  Re-raising JobAborted will
            # cause the Celery worker process to exit.
            cls, instance, tb = sys.exc_info()[0:3]
            raise TaskAborted, TaskAborted(), tb
        finally:
            aborter.stop.set()
            aborter.join()
            mlog.debug("Stopped the ABORTED status monitor thread")


class _TaskAborter(threading.Thread):
    """Stops a task if its status is set to ABORTED."""

    def __init__(self, task, tid):
        """Initialize a _TaskAborter instance.

        :param task: The currently executing task.
        :param tid: The ID of the thread executing the task.
        """
        self.task = task
        self.tid = tid
        self.request = task.request
        self.task_id = self.request.id
        self.log = self.task.log
        self.stop = threading.Event()
        super(_TaskAborter, self).__init__(name="_TaskAborter")

    def run(self):
        try:
            # Push the request and task to their respective
            # thread-local stacks.
            self.task.request_stack.push(self.request)
            push_current_task(self.task)
            result = self.task.AsyncResult(self.task_id)
            while True:
                if self._job_aborted(result):
                    break
                if self._stopped():
                    break
            if not self.stop.wait(5.0):
                mlog.warning("Forcing worker process to exit")
                os.kill(os.getpid(), signal.SIGKILL)
        finally:
            # Pop the request and task from their respective
            # thread-local stacks
            pop_current_task()
            self.task.request_stack.pop()

    def _stopped(self):
        if not self.stop.wait(0.1):
            return False
        mlog.debug("Stopping ABORTED status monitor thread")
        return True

    def _job_aborted(self, result):
        if not result.is_aborted():
            return False
        abort_mesg = "Aborting job"
        inject_mesg = "Injected the JobAbort exception"
        self.log.warning(abort_mesg)
        mlog.warning(abort_mesg)
        inject_exception_into_thread(self.tid, JobAborted)
        self.log.debug(inject_mesg)
        mlog.debug(inject_mesg)
        return True
