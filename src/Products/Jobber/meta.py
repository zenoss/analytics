##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012-2024 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function, unicode_literals

from celery import signals
from zope.configuration.exceptions import ConfigurationError
from zope.configuration.fields import GlobalObject
from zope.interface import Interface
from zope.schema import TextLine


class IJob(Interface):
    """Registers a ZenJobs task."""

    name = TextLine(title="Name", description="Unused", required=False)

    task = GlobalObject(
        title="ZenJobs Task",
        description="Path to a task class or function",
        required=False,
    )

    class_ = task  # old name for backward compatibility


def job(_context, **kw):
    """Register the task with Celery, if necessary."""
    from Products.Jobber.zenjobs import app

    task = kw.get("task")
    if task is None:
        task = kw.get("class_")
        if task is None:
            raise ConfigurationError(
                ("Missing parameter:", "'task' or 'class'")
            )

    if not task.name or task.name not in app.tasks:
        try:
            registered_task = app.register_task(task)
            registered_task.__class__.name = registered_task.name
        except Exception as e:
            raise Exception("Task registration failed: %s" % e)


class ICelerySignal(Interface):
    """Registers a Celery signal handler."""

    name = TextLine(
        title="Name",
        description="The signal receiving a handler",
    )

    handler = TextLine(
        title="Handler",
        description="Classpath to the function handling the signal",
    )


def signal(_context, name, handler):
    """Register a Celery signal handler."""
    signal = getattr(signals, name, None)
    if signal is None:
        raise AttributeError("Unknown signal name '%s'" % name)
    handler_fn = _context.resolve(handler)
    signal.connect(handler_fn)
