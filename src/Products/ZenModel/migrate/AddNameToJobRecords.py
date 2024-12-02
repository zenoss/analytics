############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

"""
Add a job_name field to JobRecord objects.  This field contains the name of
job class registered with Celery.
"""

import Migrate
from celery import current_app
from Products.Jobber.jobs import Job
from Products.Zuul.utils import safe_hasattr as hasattr


class AddNameToJobRecords(Migrate.Step):

    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        # Create a jobtype -> jobname lookup table for registered jobs.
        table = dict(
                (task.getJobType(), task.name)
                for task in (
                    t for t in current_app.tasks.values()
                        if isinstance(t, Job)
                )
            )
        # Update/add job_name field for all JobRecords.
        for rec in dmd.JobManager.getAllJobs():
            if not hasattr(rec, "job_name") or not rec.job_name:
                rec.job_name = table.get(rec.job_type)

AddNameToJobRecords()
