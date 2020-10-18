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
import os
import time

from celery import states
from celery.contrib.abortable import ABORTED
from functools import wraps
from zope.component import getUtility
from zope.interface import implementer

from Products.Zuul.interfaces import IMarshaller, IInfo

from .config import ZenJobs
from .interfaces import IJobStore, IJobRecord
from .storage import Fields
from .utils.log import inject_logger
from .zenjobs import app

mlog = logging.getLogger("zen.zenjobs.model")

sortable_keys = list(set(Fields) - {"details"})

STAGED = "STAGED"


@implementer(IJobRecord, IInfo)
class JobRecord(object):
    """Zenoss-centric record of a job submitted to ZenJobs."""

    __slots__ = tuple(key for key in Fields.keys())

    @classmethod
    def make(cls, data):
        if not (data.viewkeys() <= Fields.viewkeys()):
            bad = data.viewkeys() ^ Fields.viewkeys()
            raise AttributeError(
                "Jobrecord does not have attribute%s %s" % (
                    "" if len(bad) == 1 else "s",
                    ", ".join("'%s'" % v for v in bad),
                ),
            )
        record = cls()
        for k, v in data.viewitems():
            setattr(record, k, v)
        return record

    def __getattr__(self, name):
        # Clever hack for backward compatibility.
        # Users of JobRecord added arbitrary attributes.
        if name not in self.__slots__:
            details = getattr(self, "details", {}) or {}
            if name not in details:
                raise AttributeError(name)
            return details[name]
        return None

    def __dir__(self):
        # Add __dir__ function to expose keys of details attribute
        # as attributes of JobRecord.
        return sorted(set(
            tuple(dir(JobRecord)) +
            tuple((getattr(self, "details") or {}).keys())
        ))

    @property
    def __dict__(self):
        # Backward compatibility hack.  __slots__ objects do not have a
        # built-in __dict__ attribute.
        # Some uses of JobRecord iterated over the '__dict__' attribute
        # to retrieve job-specific/custom attributes.
        base = {
            k: getattr(self, k)
            for k in self.__slots__ + ("uuid", "duration", "complete")
            if k != "details"
        }
        details = getattr(self, "details") or {}
        base.update(**details)
        return base

    @property
    def id(self):
        """Implements IInfo.id"""
        return self.jobid

    @property
    def uid(self):
        """Implements IInfo.uid"""
        return self.jobid

    @property
    def uuid(self):
        """Alias for jobid.

        This property exists for compatiblity reasons.
        """
        return self.jobid

    @property
    def job_description(self):
        return self.description

    @property
    def job_name(self):
        return self.name

    @property
    def job_type(self):
        task = app.tasks.get(self.name)
        if task is None:
            return self.name if self.name else ""
        try:
            return task.getJobType()
        except AttributeError:
            return self.name

    @property
    def duration(self):
        if (
            self.status in (states.PENDING, states.RECEIVED)
            or self.started is None
        ):
            return None
        if self.complete:
            return self.finished - self.started
        return time.time() - self.started

    @property
    def complete(self):
        return self.status in states.READY_STATES

    def abort(self):
        """Abort the job."""
        return self.result.abort()

    def wait(self):
        return self.result.wait()

    @property
    def result(self):
        return app.tasks[self.name].AsyncResult(self.jobid)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return all(
            getattr(self, fld, None) == getattr(other, fld, None)
            for fld in self.__slots__
        )

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return any(
            getattr(self, fld, None) != getattr(other, fld, None)
            for fld in self.__slots__
        )

    def __str__(self):
        return "<{0.__class__.__name__}: {1}>".format(
            self,
            " ".join(
                "{0}={1!r}".format(name, getattr(self, name, None))
                for name in self.__slots__
            )
        )

    def __hash__(self):
        raise TypeError("unhashable type: %r" % (type(self).__name__))


@implementer(IMarshaller)
class JobRecordMarshaller(object):
    """Serializes JobRecord objects into dictionaries."""

    _default_keys = (
        "jobid",
        "summary",
        "description",
        "created",
        "started",
        "finished",
        "status",
        "userid",
    )

    def __init__(self, obj):
        """Initialize a JobRecordMarshaller object.

        :param JobRecord obj: The object to marshall
        """
        self.__obj = obj

    def marshal(self, keys=None):
        """Returns a dict containing the JobRecord's data.
        """
        fields = self._default_keys if keys is None else keys
        return {name: self._get_value(name) for name in fields}

    def _get_value(self, name):
        key = LegacySupport.from_key(name)
        return getattr(self.__obj, key, None)


class LegacySupport(object):
    """A namespace class for functions to aid in supporting legacy APIs.
    """

    # Maps legacy job record field names to their new field names.
    keys = {
        "uuid": "jobid",
        "scheduled": "created",
        "user": "userid",
    }

    @classmethod
    def from_key(cls, key):
        """Returns the modern key name for the given legacy key name."""
        return cls.keys.get(key, key)


class RedisRecord(dict):
    """A convenient mapping object for records stored in Redis.
    """

    @classmethod
    def from_task(cls, task, jobid, args, kwargs, **fields):
        if not jobid:
            raise ValueError("Invalid job ID: '%s'" % (jobid,))
        description = fields.get("description", None)
        if not description:
            description = task.description_from(*args, **kwargs)
        record = cls(
            jobid=jobid,
            name=task.name,
            summary=task.summary,
            description=description,
            logfile=os.path.join(
                ZenJobs.get("job-log-path"), "%s.log" % jobid,
            ),
        )
        if "status" in fields:
            record["status"] = fields["status"]
        if "created" in fields:
            record["created"] = fields["created"]
        if "userid" in fields:
            record["userid"] = fields["userid"]
        if "details" in fields:
            record["details"] = fields["details"]
        return record

    @classmethod
    def from_signature(cls, sig):
        """Return a RedisRecord object built from a Signature object.
        """
        taskname = sig.get("task")
        args = sig.get("args")
        kwargs = sig.get("kwargs")

        options = dict(sig.options)
        headers = options.pop("headers", {})
        jobid = options.pop("task_id")

        return cls._build(jobid, taskname, args, kwargs, headers, options)

    @classmethod
    def from_signal(cls, body, headers, properties):
        """Return a RedisRecord object built from the arguments passed to
        a before_task_publish signal handler.
        """
        jobid = body.get("id")
        taskname = body.get("task")
        args = body.get("args", ())
        kwargs = body.get("kwargs", {})
        return cls._build(jobid, taskname, args, kwargs, headers, properties)

    @classmethod
    def _build(cls, jobid, taskname, args, kwargs, headers, properties):
        task = app.tasks[taskname]
        fields = {}
        description = properties.pop("description", None)
        if description:
            fields["description"] = description
        if properties:
            fields["details"] = dict(properties)
        userid = headers.get("userid")
        if userid is not None:
            fields["userid"] = userid
        return cls.from_task(task, jobid, args, kwargs, **fields)


@inject_logger(log=mlog)
def save_jobrecord(log, body=None, headers=None, properties=None, **ignored):
    """Save the Zenoss specific job metadata to redis.

    This function is registered as a handler for the before_task_publish
    signal.  Right before the task is published to the queue, this function
    is invoked with the data to be published to the queue.

    If the task has already been saved to redis, no changes are made to the
    saved data and the function returns.

    :param dict body: Task data
    :param dict headers: Headers to accompany message sent to Celery worker
    :param dict properties: Additional task and custom key/value pairs
    """
    task, err_mesg = _verify_signal_args(body, headers, properties)
    if not task:
        log.info(err_mesg)
        return

    # If the result of tasks is ignored, there's no job record to commit.
    # Celery doesn't store an entry in the result backend when the
    # ignore_result flag is True.
    if task.ignore_result:
        return

    # Save first (and possibly only) job
    record = RedisRecord.from_signal(body, headers, properties)
    record.update({
        "status": states.PENDING,
        "created": time.time(),
    })
    saved = _save_record(log, record)

    if not saved:
        return

    # Iterate over the callbacks.
    callbacks = body.get("callbacks") or []
    links = []
    for cb in callbacks:
        links.extend(cb.flatten_links())
    for link in links:
        record = RedisRecord.from_signature(link)
        record.update({
            "status": states.PENDING,
            "created": time.time(),
        })
        _save_record(log, record)


def _save_record(log, record):
    # Retrieve the job storage connection.
    storage = getUtility(IJobStore, "redis")
    jobid = record["jobid"]
    if "userid" not in record:
        log.warn("No user ID submitted with job %s", jobid)
    if jobid not in storage:
        storage[jobid] = record
        log.info("Saved record for job %s", jobid)
        return True
    else:
        log.debug("Record already exists for job %s", jobid)
        return False


@inject_logger(log=mlog)
def stage_jobrecord(log, sig):
    """Save Zenoss specific job metadata to redis with status "STAGED".

    :param sig: The task data
    :type sig: celery.canvas.Signature
    """
    task = app.tasks.get(sig.task)

    # If the result of tasks is ignored, don't create a job record.
    # Celery doesn't store an entry in the result backend when the
    # ignore_result flag is True.
    if task.ignore_result:
        return

    record = RedisRecord.from_signature(sig)
    record.update({
        "status": STAGED,
        "created": time.time(),
    })
    _save_record(log, record)


@inject_logger(log=mlog)
def commit_jobrecord(log, body=None, headers=None, properties=None, **ignored):
    """Change a STAGED job to PENDING.

    If the task is not found in redis or does not have a status of STAGED,
    no changes are made to the task's data and this function returns.

    This function is registered as a handler for the before_task_publish
    signal.  Right before the task is published to the queue, this function
    is invoked with the data to be published to the queue.

    :param dict body: Task data
    :param dict headers: Headers to accompany message sent to Celery worker
    :param dict properties: Additional task and custom key/value pairs
    """
    task, err_mesg = _verify_signal_args(body, headers, properties)
    if not task:
        log.info(err_mesg)
        return

    # If the result of tasks is ignored, there's no job record to commit.
    # Celery doesn't store an entry in the result backend when the
    # ignore_result flag is True.
    if task.ignore_result:
        return

    jobid = body.get("id")
    storage = getUtility(IJobStore, "redis")
    if jobid not in storage:
        return

    # Skip if the status is not "STAGED".
    status = storage.getfield(jobid, "status")
    if status != STAGED:
        return

    storage.update(jobid, status=states.PENDING)


def _verify_signal_args(body, headers, properties):
    # Returns (None, str) if the args are not valid.
    # Returns (task, None) for valid arguments.
    if not body:
        # If body is empty (or None), no job to save.
        return None, "no body, so no job"

    if headers is None:
        # If headers is None, bad signal so ignore.
        return None, "no headers, bad signal?"

    task = app.tasks.get(body.get("task"))
    if task is None:
        return None, "Ignoring unknown task: {}".format(body.get("task"))

    return task, None


def _catch_exception(f):

    @wraps(f)
    def wrapper(log, *args, **kw):
        try:
            f(log, *args, **kw)
        except Exception:
            log.exception("INTERNAL ERROR")

    return wrapper


@inject_logger(log=mlog)
@_catch_exception
def job_start(log, task_id, task=None, **ignored):
    if task is not None and task.ignore_result:
        return
    jobstore = getUtility(IJobStore, "redis")
    status = jobstore.getfield(task_id, "status")

    # Don't start jobs that are finished (i.e. "ready" in Celery-speak).
    # This detects jobs that were aborted before they were executed.
    if status in states.READY_STATES:
        return

    status = states.STARTED
    tm = time.time()
    jobstore.update(task_id, status=states.STARTED, started=tm)
    log.info("status=%s started=%s", status, tm)


@inject_logger(log=mlog)
@_catch_exception
def job_end(log, task_id, task=None, **ignored):
    if task is not None and task.ignore_result:
        return
    jobstore = getUtility(IJobStore, "redis")
    finished = jobstore.getfield(task_id, "finished")
    if finished is not None:
        started = jobstore.getfield(task_id, "started")
        log.info("Job total duration is %0.3f seconds", finished - started)


@inject_logger(log=mlog)
@_catch_exception
def job_success(log, result, sender=None, **ignored):
    if sender is not None and sender.ignore_result:
        return
    task_id = sender.request.id
    jobstore = getUtility(IJobStore, "redis")
    status = app.backend.get_status(task_id)
    tm = time.time()
    jobstore.update(task_id, status=status, finished=tm)
    log.info("status=%s finished=%s", status, tm)


@inject_logger(log=mlog)
@_catch_exception
def job_failure(log, task_id, exception=None, sender=None, **ignored):
    if sender is not None and sender.ignore_result:
        return
    jobstore = getUtility(IJobStore, "redis")
    status = app.backend.get_status(task_id)
    tm = time.time()
    jobstore.update(task_id, status=status, finished=tm)
    log.info("status=%s finished=%s", status, tm)

    # Abort all subsequent jobs in the chain.
    req = getattr(sender, "request", None)
    if req is None:
        return
    callbacks = req.callbacks
    if not callbacks:
        return
    for cb in callbacks:
        cbid = cb.get("options", {}).get("task_id")
        if not cbid:
            continue
        jobstore.update(cbid, status=ABORTED, finished=tm)


@inject_logger(log=mlog)
@_catch_exception
def job_retry(log, request, reason=None, sender=None, **ignored):
    if sender is not None and sender.ignore_result:
        return
    jobstore = getUtility(IJobStore, "redis")
    task_id = request.id
    status = app.backend.get_status(task_id)
    jobstore.update(task_id, status=status)
    log.info("status=%s", status)
