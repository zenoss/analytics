##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import time
import uuid

from AccessControl.SecurityManagement import getSecurityManager
from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from ..config import getConfig
from ..utils.log import get_task_logger, get_logger

from .event import SendZenossEventMixin

_default_summary = "Task {0.__class__.__name__}"

mlog = get_logger("zen.zenjobs.task.base")


class ZenTask(SendZenossEventMixin, Task):
    """Base class for tasks."""

    abstract = True
    description_template = None
    summary = None

    throws = (SoftTimeLimitExceeded,)

    def __new__(cls, *args, **kwargs):
        task = super(ZenTask, cls).__new__(cls, *args, **kwargs)
        summary = getattr(task, "summary", None)
        if not summary:
            summary = _default_summary.format(task)
        cls.summary = summary

        task.max_retries = getConfig().get("zodb-max-retries", 5)

        return task

    @classmethod
    def description_from(cls, *args, **kwargs):
        if not cls.description_template:
            return cls.summary
        return cls.description_template.format(*args, **kwargs)

    @property
    def log(self):
        """Return the logger for this job."""
        return get_task_logger(self.name)

    @property
    def description(self):
        """Return a description of the task."""
        if not hasattr(self, "request_stack"):
            return self.summary
        req = self.request
        args = req.args if req.args else ()
        kw = req.kwargs if req.kwargs else {}
        return type(self).description_from(*args, **kw)

    def signature(self, *args, **kw):
        """Return celery.signature object for this task.

        This overridden version adds the currently logged in user's ID
        to the headers sent along with the task to Celery.

        This overridden method also sets an ID for the job.  Normally,
        Celery does not assign an ID until the job is submitted, but for
        Zenoss, the ID needs to be set before submission.
        """
        # Note that when a job is retried, this method is called when the
        # job is re-submitted.  Therefore, the current request is
        # tested before setting the values.  Nothing is set if there is a
        # currently active request.
        if self.request.headers is None:
            headers = kw.setdefault("headers", {})
            userid = getSecurityManager().getUser().getId()
            headers["userid"] = userid
        if self.request.id is None:
            kw["task_id"] = str(uuid.uuid4())
        return super(ZenTask, self).signature(*args, **kw)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        result = super(ZenTask, self).on_failure(
            exc, task_id, args, kwargs, einfo
        )
        if einfo.type in getattr(
            self, "throws", ()
        ) and not self.log.isEnabledFor(logging.DEBUG):
            # Log a simple message for known exceptions when not DEBUG.
            self.log.error("Job failed: %r", exc)
        else:
            # log the traceback for everything else.
            self.log.error("Job failed: %r\n%s", exc, einfo.traceback)

        # Always log errors for the main logger
        mlog.error("Job failed: %r", exc)

        return result

    def __call__(self, *args, **kwargs):
        """Execute the task."""
        self.__run, self.run = self.run, self.__exec
        try:
            return super(ZenTask, self).__call__(*args, **kwargs)
        finally:
            self.run = self.__run
            del self.__run

    def __exec(self, *args, **kwargs):
        self.log.info("Job started")
        mlog.debug("Job started  request=%s", self.request)
        start = time.time()
        result = self.__run(*args, **kwargs)
        stop = time.time()
        mesg = ("Job finished  duration=%0.3f", stop - start)
        mlog.debug(*mesg)
        self.log.info(*mesg)
        return result
