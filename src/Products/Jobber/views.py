##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os

from Products.Five.browser import BrowserView
from .exceptions import NoSuchJobException


class JobLogDownload(BrowserView):
    """A view for downloading job logs."""

    def __call__(self):
        """Return the contents of a job log."""
        response = self.request.response
        try:
            jobid = self.request.get("job")
            jobrecord = self.context.JobManager.getJob(jobid)
            logfile = jobrecord.logfile
        except (KeyError, AttributeError, NoSuchJobException):
            response.setStatus(404)
        else:
            response.setHeader("Content-Type", "text/plain")
            response.setHeader(
                "Content-Disposition",
                "attachment;filename=%s" % os.path.basename(logfile),
            )
            with open(logfile, "r") as f:
                return f.read()
