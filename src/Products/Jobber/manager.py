##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os
import threading

import transaction

from celery import states, chain
from transaction.interfaces import IDataManager
from zope.component import getUtility
from zope.interface import implementer

from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.ZenossSecurity import ZEN_MANAGE_DMD
from Products.Zuul.catalog.model_catalog import NoRollbackSavepoint

from .exceptions import NoSuchJobException
from .interfaces import IJobStore
from .model import (
    commit_jobrecord,
    JobRecord,
    LegacySupport,
    RedisRecord,
    sortable_keys,
    STAGED,
    stage_jobrecord,
)
from .utils.accesscontrol import ZClassSecurityInfo, ZInitializeClass
from .zenjobs import app

log = logging.getLogger("zen.zenjobs.JobManager")

JOBMANAGER_VERSION = 2

UNFINISHED_STATES = tuple(states.UNREADY_STATES) + (STAGED,)


def manage_addJobManager(context, oid="JobManager"):
    """Add the JobManager class to dmd."""
    jm = JobManager(oid)
    context._setObject(oid, jm)
    return getattr(context, oid)


@ZInitializeClass
class JobManager(ZenModelRM):
    """Manages Jobs."""

    # Attribute that allows a migration script to determine whether this
    # object should be replaced.
    _jobmanager_version = None

    security = ZClassSecurityInfo()
    meta_type = portal_type = "JobManager"

    def __init__(self, *args, **kw):
        ZenModelRM.__init__(self, *args, **kw)
        self._jobmanager_version = JOBMANAGER_VERSION

    @security.protected(ZEN_MANAGE_DMD)
    def addJobChain(self, *joblist, **options):
        """Submit a list of Signature objects that will execute in list order.

        If options are specified, they are applied to each subjob; options
        that were specified directly on the subjob are not overridden.

        Supported options include:
            immutable {bool} Set True to 'freeze' the job arguments.
            ignoreresult {bool} Set True to drop the result of the jobs.

        If both options are not set, they default to False, which means the
        result of the prior job is passed to the next job as argument(s).

        NOTE: The jobs WILL NOT run until the current transaction is committed!

        :param joblist: task signatures as positional arguments
        :type joblist: Tuple[celery.canvas.Signature]
        :param options: additional options/settings to apply to each job
        :type options: Dict[str, Any]
        :return: The job record objects associated with the jobs.
        :rtype: Tuple[JobRecord]
        """
        signatures = []
        for signature in joblist:
            signature = signature.set(**options)
            signatures.append(signature)
        job = chain(*signatures)

        # Defer sending the job until the transaction has been committed.
        _job_dispatcher.add(job)

        return tuple(
            JobRecord.make(RedisRecord.from_signature(s)) for s in signatures
        )

    @security.protected(ZEN_MANAGE_DMD)
    def addJob(
        self,
        jobclass,
        description=None,
        args=None,
        kwargs=None,
        properties=None,
    ):
        """Schedule a new job for execution.

        NOTE: The job WILL NOT run until the current transaction is committed!

        :type jobclass: Task
        :type description: Union[str, None]
        :type args: Union[Sequence[Any], None]
        :type kwargs: Union[Mapping[str, Any], None]
        :type properties: Union[Mapping[str, Any], None]
        :return: The job record of the submitted job
        :rtype: JobRecord
        """
        args = args or ()
        kwargs = kwargs or {}
        properties = properties or {}

        # Retrieve the task object
        task = app.tasks.get(jobclass.name)
        if task is None:
            raise NoSuchJobException("No such job '%s'" % jobclass.name)

        if description is not None:
            properties["description"] = description

        # Build the signature to call the task
        s = task.s(*args, **kwargs).set(**properties)

        # Defer sending the job until the transaction has been committed.
        _job_dispatcher.add(s)

        return JobRecord.make(RedisRecord.from_signature(s))

    def wait(self, jobid):
        """Wait for the job identified by jobid to complete.

        :param str jobid: The ID of the job.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        status = storage.getfield(jobid, "status")
        if status == STAGED and jobid not in _job_dispatcher.staged:
            raise NoSuchJobException(jobid)
        taskname = storage.getfield(jobid, "name")
        app.tasks.get(taskname).AsyncResult(jobid).wait()

    def query(
        self,
        criteria=None,
        key="created",
        reverse=False,
        offset=0,
        limit=None,
    ):
        """Return jobs matching the provided criteria.

        Criteria fields:
            status - Select only records with this status
            user/userid - Select only records with this user ID

        Sort arguments:
            key - Result is sorted by this field
            reverse - True to reverse the sort order
            offset - The returned result starts with this index
            limit - Maximum number of returned records.

        Supported values for 'key':
            jobid
            name
            summary
            description
            userid
            logfile
            created
            started
            finished
            status
            uuid
            scheduled
            user

        :type criteria: Mapping[str, Union[int, float, str]]
        :type key: str
        :type reverse: boolean
        :type offset: int
        :type limit: Union[int, None]
        :rtype: {"jobs": Tuple[JobRecord], "total": int}
        """
        criteria = criteria if criteria is not None else {}
        normalized_criteria = {
            LegacySupport.from_key(k): criteria[k] for k in criteria
        }
        valid = ["status", "userid"]
        invalid_fields = set(normalized_criteria.keys()) - set(valid)
        if invalid_fields:
            raise ValueError(
                "Invalid criteria field: %s" % ", ".join(invalid_fields),
            )
        normalized_key = LegacySupport.from_key(key)
        if normalized_key not in sortable_keys:
            raise ValueError("Invalid sort key: %s" % (key,))
        try:
            storage = getUtility(IJobStore, "redis")
            if len(normalized_criteria):
                jobids = storage.search(**normalized_criteria)
                records = storage.mget(*jobids)
            else:
                records = storage.values()
            # For an accurate count of all results, unknown STAGED jobs
            # are removed from the original result.
            staged_task_ids = _job_dispatcher.staged
            result = sorted(
                (
                    rec
                    for rec in records
                    if rec["status"] != STAGED
                    or rec["jobid"] in staged_task_ids
                ),
                key=lambda x: x[normalized_key],
                reverse=reverse,
            )
            end = len(result) if limit is None else offset + limit
            jobs = tuple(JobRecord.make(rec) for rec in result[offset:end])
            return {"jobs": jobs, "total": len(result)}
        except Exception:
            log.exception("Internal Error")
            return {"jobs": (), "total": 0}

    def update(self, jobid, **kwargs):
        """Add or update job specific properties.

        :param str jobid: The ID of the job.
        :param **kwargs: The job-specific properties.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        status = storage.getfield(jobid, "status")
        if status == STAGED and jobid not in _job_dispatcher.staged:
            raise NoSuchJobException(jobid)
        storage.update(jobid, details=kwargs)

    def getJob(self, jobid):
        """Return the job identified by jobid.

        If no job exists with the given ID, a NoSuchJobException is raised.

        :param str jobid: The ID of the job.
        :rtype: JobRecord
        :raises NoSuchJobException: If jobid doesn't exist.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            raise NoSuchJobException(jobid)
        status = storage.getfield(jobid, "status")
        if status == STAGED and jobid not in _job_dispatcher.staged:
            raise NoSuchJobException(jobid)
        return JobRecord.make(storage[jobid])

    @security.protected(ZEN_MANAGE_DMD)
    def deleteJob(self, jobid):
        """Delete the job data identified by jobid.

        :param str jobid: The ID of the job to delete.
        """
        storage = getUtility(IJobStore, "redis")
        if jobid not in storage:
            log.warn("Cannot delete job that does not exist: %s", jobid)
            return
        job = storage[jobid]

        if job["status"] == STAGED:
            if jobid in _job_dispatcher.staged:
                _job_dispatcher.discard(jobid)
            return

        if job.get("status") not in states.READY_STATES:
            task = app.tasks[job["name"]]
            result = task.AsyncResult(jobid)
            result.abort()
        # Clean up the log file
        logfile = job.get("logfile")
        if logfile is not None:
            try:
                os.remove(logfile)
            except (OSError, IOError):
                # Did our best!
                pass
        del storage[jobid]
        log.info("Job deleted  jobid=%s name=%s", jobid, job["name"])

    def getUnfinishedJobs(self, type_=None):
        """Return jobs that are not completed.

        Includes jobs that have not started.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        result = _getByStatusAndType(UNFINISHED_STATES, type_)
        # Filter out STAGED jobs the caller shouldn't know about.
        staged_task_ids = _job_dispatcher.staged
        return (
            job
            for job in result
            if job.status != STAGED or job.jobid in staged_task_ids
        )

    def getRunningJobs(self, type_=None):
        """Return the jobs that have started but not not finished.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType((states.STARTED, states.RETRY), type_)

    def getPendingJobs(self, type_=None):
        """Return the jobs that have not yet started.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType((states.RECEIVED, states.PENDING), type_)

    def getFinishedJobs(self, type_=None):
        """Return the jobs that have finished.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        return _getByStatusAndType(states.READY_STATES, type_)

    def getAllJobs(self, type_=None):
        """Return all jobs.

        :param type_: Filter results on this Job type.
        :type type_: Union[str, Type[Task]]
        :return: All jobs in the requested state.
        :rtype: Iterator[JobRecord]
        """
        storage = getUtility(IJobStore, "redis")
        if type_ is not None:
            jobtype = _getJobTypeStr(type_)
            jobids = storage.search(name=jobtype)
            result = storage.mget(*jobids)
        else:
            result = storage.values()
        staged_task_ids = _job_dispatcher.staged
        return (
            JobRecord.make(rec)
            for rec in result
            if rec["status"] != STAGED or rec["jobid"] in staged_task_ids
        )

    @security.protected(ZEN_MANAGE_DMD)
    def clearJobs(self):
        """Delete all finished jobs."""
        storage = getUtility(IJobStore, "redis")
        jobids = tuple(storage.search(status=states.READY_STATES))
        logfiles = (storage.getfield(j, "logfile") for j in jobids)
        for logfile in (lf for lf in logfiles if lf is not None):
            if os.path.exists(logfile):
                try:
                    os.remove(logfile)
                except (OSError, IOError):
                    pass
        storage.mdelete(*jobids)

    @security.protected(ZEN_MANAGE_DMD)
    def killRunning(self):
        """Abort running jobs."""
        for job in self.getUnfinishedJobs():
            job.abort()


@implementer(IDataManager)
class JobDispatcher(object):
    """ """

    transaction_manager = transaction.manager.manager

    def __init__(self, storage):
        self._storage = storage
        self._joined = False
        self._signatures = []
        self._staged = []

    @property
    def staged(self):
        return tuple(task.id for task in self._staged)

    def add(self, sig):
        if not self._joined:
            transaction.get().join(self)
            self._joined = True

        # The 'tasks' attribute appears only on canvas tasks, e.g. chain.
        tasks = getattr(sig, "tasks", (sig,))
        for task in tasks:
            stage_jobrecord(self._storage, task)

        self._staged.extend(tasks)
        self._signatures.append(sig)

    def discard(self, task_id):
        self._staged = [task for task in self._staged if task.id != task_id]
        self._storage.mdelete(*(task_id,))
        self._signatures = [
            task for task in self._signatures if task.id != task_id
        ]

    def _reset(self):
        self._joined = False
        self._signatures = []
        self._staged = []

    # ==========
    # IDataManager interface methods follow below

    def abort(self, tx):
        # Delete staged records
        self._storage.mdelete(*(task.id for task in self._staged))
        self._reset()
        log.debug("[abort] discarded staged job")

    def tpc_begin(self, tx):
        # Required by IDataManager, but a no-op for JobDispatcher
        pass

    def commit(self, tx):
        # Required by IDataManager, but a no-op for JobDispatcher
        pass

    def tpc_vote(self, tx):
        # Required by IDataManager, but a no-op for JobDispatcher
        pass

    def tpc_finish(self, tx):
        # Update relevant STAGED records to PENDING.
        for task in self._staged:
            commit_jobrecord(self._storage, task)
        # Send the job(s) to zenjobs
        for sig in self._signatures:
            sig.apply_async()
        self._reset()
        log.debug("[tpc_finish] set staged jobs to pending; dispatched job")

    def tpc_abort(self, tx):
        self.abort(tx)

    def sortKey(self):
        return str(id(self))

    def savepoint(self, optimistic=False):
        return NoRollbackSavepoint(self)


class ThreadedJobDispatcher(threading.local):
    def __getattr__(self, name):
        # Lazily initialize 'dispatcher'; avoids performing zope component
        # lookups during module loading.
        # This is not evaluated each time because __getattr__ is called
        # only when an attribute is not found.
        if name == "dispatcher":
            storage = getUtility(IJobStore, "redis")
            dispatcher = self.dispatcher = JobDispatcher(storage)
            return dispatcher
        return super(ThreadedJobDispatcher, self).__getattr__(name)

    def add(self, sig):
        self.dispatcher.add(sig)

    def discard(self, taskid):
        self.dispatcher.discard(taskid)

    @property
    def staged(self):
        return self.dispatcher.staged


_job_dispatcher = ThreadedJobDispatcher()


def _getByStatusAndType(statuses, jobtype=None):
    fields = {"status": statuses}
    if jobtype is not None:
        fields["name"] = _getJobTypeStr(jobtype)
    storage = getUtility(IJobStore, "redis")
    jobids = storage.search(**fields)
    result = storage.mget(*jobids)
    return (JobRecord.make(jobdata) for jobdata in result)


def _getJobTypeStr(jobtype):
    if isinstance(jobtype, type):
        name = jobtype.name
    else:
        task = app.tasks.get(str(jobtype))
        if not task:
            raise ValueError("No such task: {!r}".format(jobtype))
        name = task.name
    if name is None:
        raise ValueError("zenjobs task name is None: {!r}".format(jobtype))
    return name
