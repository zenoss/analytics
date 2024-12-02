##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from datetime import timedelta
from zope.component import getUtility

import Products.ZenUtils.guid as guid

from Products.ZenEvents import Event
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher

from ..utils.datetime import humanize_timedelta
from ..utils.log import get_logger

mlog = get_logger("zen.zenjobs.task.event")


class SendZenossEventMixin(object):
    """Mixin class to send an Zenoss event when a job fails."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            return super(SendZenossEventMixin, self).on_failure(
                exc, task_id, args, kwargs, einfo
            )
        finally:
            try:
                _send_event(self, exc, task_id, args, kwargs)
            except Exception:
                mlog.exception("Failed to send event")


def _send_event(task, exc, task_id, args, kwargs):
    classkey, summary = _getErrorInfo(task, exc)
    name = task.getJobType() if hasattr(task, "getJobType") else task.name
    publisher = getUtility(IEventPublisher)
    event = Event.Event(
        **{
            "evid": guid.generate(1),
            "device": name,
            "severity": Event.Error,
            "component": "zenjobs",
            "eventClassKey": classkey,
            "eventKey": "{}|{}".format(classkey, name),
            "message": task.description_from(*args, **kwargs),
            "summary": summary,
            "jobid": str(task_id),
        }
    )
    publisher.publish(event)
    log_message = (
        "Event sent  event-class-key=%s summary=%s",
        classkey,
        summary,
    )
    task.log.info(*log_message)
    mlog.info(*log_message)


def _getTimeoutSummary(task, ex):
    _, soft_limit = task.request.timelimit or (None, None)
    if soft_limit is None:
        soft_limit = task.app.conf.get("task_soft_time_limit")
    return "Job timed out after {}.".format(
        humanize_timedelta(timedelta(seconds=soft_limit))
    )


def _getAbortedSummary(task, ex):
    return "Job aborted by user"


def _getErrorSummary(task, ex):
    return "{0.__class__.__name__}: {0}".format(ex)


_error_eventkey_map = {
    "TaskAborted": ("zenjobs-aborted", _getAbortedSummary),
    "SoftTimeLimitExceeded": ("zenjobs-timeout", _getTimeoutSummary),
}


def _getErrorInfo(task, ex):
    """Returns (eventkey, summary)."""
    key, summary_fn = _error_eventkey_map.get(
        type(ex).__name__, ("zenjobs-failure", _getErrorSummary)
    )
    return key, summary_fn(task, ex)
