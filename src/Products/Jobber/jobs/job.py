##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from ..config import getConfig
from ..exceptions import NoSuchJobException
from ..task import Abortable, DMD, ZenTask
from ..zenjobs import app

_MARKER = object()


class Job(Abortable, DMD, ZenTask):
    """Base class for legacy jobs."""

    abstract = True  # Job class itself is not registered.

    # Specifying the exceptions a job can raise will avoid the
    # "Unexpected exception" traceback message in zenjobs' log.
    throws = Abortable.throws + ZenTask.throws

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job.

        By default, the class type name is returned.
        """
        return cls.name

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        """Return the description of the task instance."""
        raise NotImplementedError

    @classmethod
    def description_from(cls, *args, **kwargs):
        """Alias for getJobDescription."""
        return cls.getJobDescription(*args, **kwargs)

    @classmethod
    def makeSubJob(cls, args=None, kwargs=None, description=None, **options):
        """Return a celery.canvas.Signature instance.

        The Signature instance wraps the given job, its arguments, and options.
        """
        task = app.tasks.get(cls.name)
        if task is None:
            raise NoSuchJobException(
                "No job named '{}' is registered".format(cls.name),
            )
        args = args or ()
        kwargs = kwargs or {}
        # Build the task's call signature
        signature = task.s(*args, **kwargs).set(**options)
        # Add 'description' if given
        if description:
            signature = signature.set(description=description)
        return signature

    def __call__(self, *args, **kwargs):
        """Execute the job."""
        # Make the 'run' method an alias for the '_run' method, so
        # that legacy Job-based tasks match the celery.Task API.
        self.run = self._run
        return super(Job, self).__call__(*args, **kwargs)

    def setProperties(self, **properties):
        jobid = self.request.id
        if not jobid:
            return
        record = self.dmd.JobManager.getJob(jobid)
        details = record.details or {}
        details.update(**properties)
        self.dmd.JobManager.update(jobid, **details)

    def _get_config(self, key, default=_MARKER):
        value = getConfig().get(key, default)
        if value is _MARKER:
            raise KeyError("Config option '{}' is not defined".format(key))
        return value

    def _run(self, *args, **kw):
        raise NotImplementedError(
            "Not implemented: {0.__class__.__name__}._run".format(self),
        )
