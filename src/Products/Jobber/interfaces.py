##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, unicode_literals

from celery import states
from zope.interface import Interface
from zope.schema import Bool, Choice, Datetime, TextLine, Timedelta
from zope.schema.vocabulary import SimpleVocabulary


class IJobRecord(Interface):
    """ """

    jobid = TextLine(
        title="Job ID",
        description="The Job's unique identifier",
    )

    name = TextLine(
        title="Name",
        description="The full class name of the job",
    )

    summary = TextLine(
        title="Summary",
        description="A brief and general summary of the job's function",
    )

    description = TextLine(
        title="Description",
        description="A description of what this job will do",
    )

    userid = TextLine(
        title="User ID",
        description="The user that created the job",
    )

    logfile = TextLine(
        title="Logfile",
        description="Path to this job's log file.",
    )

    status = Choice(
        title="Status",
        description="The current status of the job",
        vocabulary=SimpleVocabulary.fromValues(states.ALL_STATES),
    )

    created = Datetime(
        title="Created",
        description="When the job was created",
    )

    started = Datetime(
        title="Started",
        description="When the job began executing",
    )

    finished = Datetime(
        title="Finished",
        description="When the job finished executing",
    )

    duration = Timedelta(
        title="Duration",
        description="How long the job has run",
    )

    complete = Bool(
        title="Complete",
        description="True if the job has finished running",
    )

    def abort():
        """Abort the job."""

    def wait(timeout=10.0):
        """Wait until the job has completed or the timeout duration has
        been exceeded before returning.
        """


class IJobStore(Interface):
    """Interface tag for JobStore."""
