##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import six

from AccessControl import getSecurityManager
from Products.Zuul.facades import ZuulFacade

log = logging.getLogger('zen.JobsFacade')


class JobsFacade(ZuulFacade):
    """Facade for JobManager."""

    def queryJobs(
        self, start=0, limit=50, sort='created', dir='ASC', createdBy=None,
    ):
        """Returns the requested job records.

        :return: A tuple containing the jobs and the total number of jobs.
        :rtype: Tuple[Sequence[JobRecord], int]
        """
        start = max(start, 0)
        queryArgs = {
            "key": sort,
            "reverse": (dir == "DESC"),
            "offset": start,
            "limit": limit,
        }
        if createdBy is not None:
            queryArgs["criteria"] = {"userid": createdBy}
        log.debug("queryArgs %s", queryArgs)
        result = self._dmd.JobManager.query(**queryArgs)
        return (
            result["jobs"],
            result["total"],
        )

    def getJob(self, jobid):
        """Returns the job record identified by jobid.

        :type jobid: str
        :rtype: JobRecord
        """
        return self._dmd.JobManager.getJob(jobid)

    def abortJob(self, jobid):
        """Aborts the job record identified by jobid.

        :type jobid: str
        """
        self._dmd.JobManager.getJob(jobid).abort()

    def deleteJob(self, jobid):
        """Deletes the job record identified by jobid.

        :type jobid: str
        """
        self._dmd.JobManager.deleteJob(jobid)

    def getJobLog(self, jobid):
        """Returns the last 100 lines of the job's log file.

        The return value is a tuple structured as follows:

            (<logfile>, <list of str>, <True if list is truncated log>)

        If there's no log file the returned tuple's structure is:

            (<error message>, (), None)

        :type jobid: str
        :rtype: Tuple[str, Tuple[str], Union[boolean, None]]
        """
        job = self._dmd.JobManager.getJob(jobid)
        try:
            with open(job.logfile, 'r') as f:
                _buffer = f.readlines()
                return (
                    job.logfile,
                    tuple(_buffer[-100:]),
                    len(_buffer) > 100,
                )
        except (IOError, AttributeError):
            return (
                (
                    "The log file for this job either does not exist or "
                    "cannot be accessed."
                ),
                (),
                None,
            )

    def getUserJobs(self, statuses=None):
        """Returns the jobs associated with the current user.

        :rtype: Tuple[JobRecord]
        """
        user = getSecurityManager().getUser()
        if not isinstance(user, six.string_types):
            user = user.getId()
        criteria = {"userid": user}
        if statuses:
            criteria["status"] = statuses
        return self._dmd.JobManager.query(criteria=criteria)["jobs"]
