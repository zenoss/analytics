##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from Products.ZenUtils.Threading import ThreadInterrupt


class JobAborted(ThreadInterrupt):
    """The job has been aborted.

    This exception derives from ThreadInterrupt which itself is derived
    from BaseException.  Using BaseException is useful to increase the
    chance of bypassing exception handlers within a job implementation
    which could prevent the job execution from stopping.
    """


class TaskAborted(Exception):
    """The task has been aborted.

    This is similiar to JobAborted, but derives from Exception instead of
    BaseException.

    The TaskAborted exception is used to communicate to Celery to 'fail' the
    job.  The JobAborted exception cannot be used; since its base is
    BaseException, it will cause the Celery worker to exit.  So when
    JobAborted is raised, it is converted to a TaskAborted exception and
    then raised for Celery to handle.
    """


class NoSuchJobException(Exception):
    """No such job exists."""


class JobAlreadyExistsException(Exception):
    """A matching job has already been submitted, and is not yet finished."""


class SubprocessJobFailed(Exception):
    """A subprocess job exited with a non-zero return code."""


class FacadeMethodJobFailed(Exception):
    """A facade method job failed."""
