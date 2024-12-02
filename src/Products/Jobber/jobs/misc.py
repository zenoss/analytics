##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import sys
import threading

from ZODB.POSException import ConflictError

from ..task import requires, DMD, Abortable
from ..zenjobs import app
from .job import Job


class DeviceListJob(Job):
    """Return the names of Server/Linux devices."""

    name = "zen.zenjobs.test.DeviceListJob"
    ignore_result = False

    @classmethod
    def getJobDescription(cls, *args, **kwargs):
        return "some description"

    def _run(self, *args, **kw):
        deviceNames = [
            device.id for device in self.dmd.Devices.Server.Linux.devices()
        ]
        # attrs = ", ".join(dir(self))
        self.log.info("device names: %s", deviceNames)
        return deviceNames


class PausingJob(Job):
    """Waits for some interval of time before finishing successfully."""

    name = "zen.zenjobs.test.PausingJob"

    @classmethod
    def getJobDescription(cls, *args, **kw):
        return "Runs for %s seconds" % args[0]

    def _run(self, seconds, *args, **kw):
        self.log.info("Sleeping for %s seconds", seconds)
        threading.Event().wait(seconds)


class DelayedFailureError(ValueError):
    pass


class DelayedFailure(Job):
    """Waits for some interval of time before failing."""

    name = "zen.zenjobs.test.DelayedFailure"
    throws = Job.throws + (DelayedFailureError,)

    @classmethod
    def getJobDescription(cls, *args, **kw):
        return "Runs for %s seconds before failing" % args[0]

    def _run(self, seconds, *args, **kw):
        self.log.info("Sleeping for %s seconds", seconds)
        threading.Event().wait(seconds)
        raise DelayedFailureError("slept for %s seconds" % seconds)


app.register_task(DeviceListJob)
app.register_task(PausingJob)
app.register_task(DelayedFailure)


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="zen.zenjobs.test.badtx",
    summary="Test ConflictError handling",
)
def badtx(self):
    raise ConflictError("boom")


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="zen.zenjobs.test.pathexists",
    summary="Test whether a ZODB UID exists",
    description_template="Test whether {0} exists in ZODB.",
)
def pathexists(self, uid):
    try:
        obj = self.dmd.unrestrictedTraverse(uid)
        self.log.info("Found object %s: %s", uid, obj)
        return True
    except Exception:
        self.log.exception("Had a problem finding %s", uid)
        return False


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="zen.zenjobs.test.pause",
    summary="Wait Task",
    description_template="Wait for {0} seconds, then exit.",
)
def pause(self, seconds):
    self.log.info("Sleeping for %s seconds", seconds)
    threading.Event().wait(seconds)


@app.task(
    bind=True,
    base=requires(DMD, Abortable),
    name="zen.zenjobs.test.rolesgroups",
    summary="Log roles and groups of user",
    description_template="Log roles and groups of user",
)
def rolesgroups(self):
    from Products.Zuul.utils import allowedRolesAndGroups

    self.log.info(allowedRolesAndGroups(self.dmd))


@app.task(
    bind=True,
    name="zen.zenjobs.test.loggertest",
    summary="Test different loggers",
    description_template="Test the task logger, zen logger, etc.",
)
def loggertest(self):
    self.log.info("This is a test")
    logging.getLogger("zen").info("This is a test")
    logging.getLogger("zen.Device").info("This is a test")
    stdout = logging.getLogger("STDOUT")
    stderr = logging.getLogger("STDERR")

    print("(stdout) This is a test")
    stdout.debug("Written directly to STDOUT logger")
    stdout.info("Written directly to STDOUT logger")
    stdout.warn("Written directly to STDOUT logger")
    stdout.error("Written directly to STDOUT logger")
    stdout.critical("Written directly to STDOUT logger")

    print("(stderr) This is a test", file=sys.stderr)
    stderr.debug("Written directly to STDERR logger")
    stderr.info("Written directly to STDERR logger")
    stderr.warn("Written directly to STDERR logger")
    stderr.error("Written directly to STDERR logger")
    stderr.critical("Written directly to STDERR logger")

    self.log.info(
        "stderr's effective log level is %s",
        logging.getLevelName(stderr.getEffectiveLevel()),
    )
    self.log.info(
        "stderr's log level is %s", logging.getLevelName(stderr.level)
    )
    self.log.info("stderr.propagate -> %s", stderr.propagate)
    self.log.info(
        "stdout's effective log level is %s",
        logging.getLevelName(stdout.getEffectiveLevel()),
    )
    self.log.info(
        "stdout's log level is %s", logging.getLevelName(stdout.level)
    )
    self.log.info("stdout.propagate -> %s", stdout.propagate)
    rootlog = logging.getLogger()
    self.log.info(
        "rootlog's effective log level is %s",
        logging.getLevelName(rootlog.getEffectiveLevel()),
    )
    self.log.info(
        "rootlog's log level is %s", logging.getLevelName(rootlog.level)
    )
