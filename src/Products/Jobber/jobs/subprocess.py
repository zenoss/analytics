##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os
import subprocess
import threading
import time

from contextlib import contextmanager

from Products.ZenUtils.Threading import LineReader

from ..exceptions import SubprocessJobFailed, JobAborted
from ..utils.log import TaskLogFileHandler
from .job import Job


class SubprocessJob(Job):
    """Use this job to execute shell commands."""

    name = "Products.Jobber.SubprocessJob"

    # Specifying the exceptions a job can raise will avoid the
    # "Unexpected exception" traceback message in zenjobs' log.
    # NOTE: JobAborted is not specified on purpose.  The Abortable base
    # class catches JobAborted and handles it.  Also, JobAborted does
    # not originate from the SubprocessJob class so it has no business
    # specifying whether it's an expected exception.
    throws = Job.throws + (SubprocessJobFailed,)

    @classmethod
    def getJobType(cls):
        """Return a general, but brief, description of the job."""
        return "Shell Command"

    @classmethod
    def getJobDescription(cls, cmd, environ=None):
        """Return a description of the job."""
        return cmd if isinstance(cmd, basestring) else " ".join(cmd)

    def _run(self, cmd, environ=None):
        self.log.debug("Running Job %s %s", self.getJobType(), cmd)
        if environ is not None and isinstance(environ, dict):
            newenviron = os.environ.copy()
            newenviron.update(environ)
            environ = newenviron
        else:
            environ = None
        process = None
        try:
            try:
                self.log.info(
                    "Spawning subprocess: %s", self.getJobDescription(cmd)
                )
                start = time.time()
                process = subprocess.Popen(
                    cmd,
                    bufsize=1,
                    env=environ,
                    close_fds=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
            except Exception as ex:
                summary = str(ex)
                message = "Error executing command %s: %s" % (
                    self.getJobDescription(cmd),
                    ex,
                )
            else:
                exitcode, output = self._handle_process(process)
                stop = time.time()
                self.log.info("Command ran for %0.3f seconds", stop - start)
                if exitcode == 0:
                    return exitcode
                summary = "Command failed with exit code %s" % exitcode
                message = "Exit code %s for command %s; %s" % (
                    exitcode,
                    self.getJobDescription(cmd),
                    output,
                )
            self.log.error(message)
            raise SubprocessJobFailed(summary)
        except JobAborted:
            if process:
                self.log.warn("Job aborted. Killing subprocess...")
                process.kill()
                process.wait()  # clean up the <defunct> process
                self.log.info("Subprocess killed.")
            raise

    def _handle_process(self, process):
        process.stdout.flush()
        # Since process.stdout.readline() is a blocking call, it stops
        # asynchronous actions from occurring until it unblocks.
        # The LineReader object allows non-blocking readline().
        reader = LineReader(process.stdout)
        try:
            reader.start()

            # Use threading.Event for temporarily pausing the thread
            # because time.sleep blocks the current thread preventing it
            # from receiving a JobAborted exception in a timely manner.
            _sleeper = threading.Event()

            formatting_context = getLogFormattingContext()
            exitcode = None
            output = ""
            while exitcode is None:
                line = reader.readline()
                if line:
                    line = line.rstrip()
                    with formatting_context():
                        self.log.info(line)
                        output += line
                else:
                    exitcode = process.poll()
                    _sleeper.wait(0.1)
            return exitcode, output
        finally:
            reader.join(timeout=1.0)


from Products.Jobber.zenjobs import app
app.register_task(SubprocessJob)


@contextmanager
def null_context():
    """Do nothing context manager."""
    yield


class LogFormatterContext(object):
    """Context manager that changes log formatter temporarily."""

    def __init__(self, handler, formatter):
        self.__handler = handler
        self.__original = handler.formatter
        self.__alternate = formatter

    def __call__(self):
        return self

    def __enter__(self):
        self.__handler.setFormatter(self.__alternate)

    def __exit__(self, *ignored):
        self.__handler.setFormatter(self.__original)


def getLogFormattingContext():
    """Returns a context manager."""
    zenlog = logging.getLogger("zen")
    handler = next(
        (h for h in zenlog.handlers if isinstance(h, TaskLogFileHandler)), None
    )
    if handler:
        return LogFormatterContext(handler, logging.Formatter("%(message)s"))
    return null_context


def _getLogHandler(log):
    # Retrieve the formatter from the handler.
    # However, the current logger may not have any handlers, so traverse
    # the parent loggers until a logger with handlers is found.
    while log and not log.handlers:
        log = log.parent
    return log.handlers[0]
