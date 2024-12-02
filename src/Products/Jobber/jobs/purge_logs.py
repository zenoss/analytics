##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import os

from ..config import getConfig
from ..task import requires, Abortable
from ..zenjobs import app


@app.task(
    bind=True,
    base=requires(Abortable),
    name="zen.zenjobs.purge_logs",
    summary="Delete the logs of deleted jobs",
    ignore_result=True,
)
def purge_logs(self):
    backend = app.backend
    saved_keys = set(
        key.replace(backend.task_keyprefix, "")
        for key in backend.client.keys("%s*" % backend.task_keyprefix)
    )
    logpath = getConfig().get("job-log-path")
    logfiles = os.listdir(logpath)
    if not logfiles:
        self.log.info("No log files to remove")
    removed = []
    for logfile in logfiles:
        keyname = logfile.rstrip(".log")
        if keyname not in saved_keys:
            try:
                os.remove(os.path.join(logpath, logfile))
                self.log.info("Removed %s", logfile)
                removed.append(logfile)
            except Exception as ex:
                self.log.error("Could not remove %s: %s", logfile, ex)
    self.log.info("Removed %s log files", len(removed))
