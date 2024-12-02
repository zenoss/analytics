##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import inspect

from itertools import chain

from zope.component import getUtility

from ..interfaces import IJobStore


def requires(*features):
    """Return a custom Task deriving from the given features.

    The method resolution order of the created custom task class is
    (*features, ZenTask, celery.app.task.Task, object) where 'features'
    are the classes given to this function.
    """
    from ..zenjobs import app

    bases = tuple(features) + (app.Task, object)
    culled = []
    for feature in reversed(bases):
        for cls in reversed(inspect.getmro(feature)):
            if cls not in culled:
                culled.insert(0, cls)
    name = "".join(t.__name__ for t in features) + "Task"
    throws = set(
        chain.from_iterable(getattr(cls, "throws", ()) for cls in culled)
    )
    basetask = type(
        name, tuple(culled), {"abstract": True, "throws": tuple(throws)}
    )
    return basetask


_failure_text = (
    "ERROR zen.",
    "ERROR STDERR",
    "CRITICAL zen.",
    "CRITICAL STDERR",
)


def job_log_has_errors(task_id):
    """Return True if the job's log contains any ERROR messages."""
    storage = getUtility(IJobStore, "redis")
    logfile = storage.getfield(task_id, "logfile")
    if not logfile:
        return False
    try:
        with open(logfile, "r") as f:
            return any(
                any(txt in line for txt in _failure_text)
                for line in f.readlines()
            )
    except Exception:
        return False
