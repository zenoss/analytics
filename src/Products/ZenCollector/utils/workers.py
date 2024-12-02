##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import ctypes
import logging
import multiprocessing
import optparse
import os
import signal
import sys

from ctypes.util import find_library
from time import sleep

from twisted.internet import reactor

from Products.ZenUtils.CmdBase import remove_args

log = logging.getLogger("zen.workers")

MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS = 5  # ask it nicely and wait.
MAX_SECONDS_TO_FORCE_KILL_WORKERS = 5  # loop "kill -9" then give up.


def workersBuildOptions(parser, default=1):
    """
    Adds option for number or workers
    """
    parser.add_option(
        "--workers", type="int", default=default, help=optparse.SUPPRESS_HELP
    )


def exec_worker(worker_id=None):
    """
    used to create a worker for an existing zenoss daemon. Removes the
    "workers" and "daemon" sys args and replace the current process by
    executing sys args
    """

    # Here we are just registering parents death signal as this childs terminal
    # signal as well.
    # When the parent dies (for whatever reason), the child will get SIGTERM.
    libc = ctypes.CDLL(find_library("c"))
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

    argv = [sys.executable]
    # Remove unwanted parameters from worker processes
    argv.extend(
        remove_args(
            sys.argv[:], ["-D", "--daemon", "-c", "--cycle"], ["--workerid"]
        )
    )
    if worker_id is not None:
        argv.append("--workerid=%d" % worker_id)
    # Tell the worker process to log to the log file and not just to console
    argv.append("--duallog")
    try:
        log.info("starting worker process")
        os.execvp(argv[0], argv)
    except Exception:
        log.exception("Failed to start process")


class ProcessWorkers(object):
    """
    class for starting and restarting Multiprocessing process from
    within a twisted reactor.
    If workerTarget is None then exec_worker is chosen by default.
    """

    def __init__(self, maxWorkers, workerTarget=None, workerName=None):
        self._maxWorkers = maxWorkers
        self._workerTarget = workerTarget
        self._workerName = workerName
        # keeps track of number of workers started and restarted
        self._workerCount = 0
        self._workers = {}
        self._checking = False
        self._shutdown = False

    def _sigchldhandler(self, signum=None, frame=None):
        if not self._shutdown:
            log.debug("_sigchldhandler reactor checkworkers")
            reactor.callLater(1, self.checkWorkers)
        else:
            log.debug("_sigchldhandler: shutting down, skipping")

    def sendSignal(self, signum):
        for worker in self._workers.values():
            log.debug("Sending signal %s to %s", signum, worker.pid)
            os.kill(worker.pid, signum)

    def startWorkers(self):
        def _doStart():
            for i in xrange(1, self._maxWorkers + 1):
                self._workers[i] = self._startWorker(str(i))
            log.debug("Registering SIGCHLD handler")
            signal.signal(signal.SIGCHLD, self._sigchldhandler)

        reactor.callWhenRunning(_doStart)

    def shutdown(self):
        """
        Workers can be in one of four states:
            Not fully started yet
                -- is_alive False, ignores SIGTERM, can't SIGKILL
            Started but not initialized
                -- is_alive True,  ignores SIGTERM, can SIGKILL
            Initialized
                -- is_alive True,  SIGTERM will terminate it
            Died early
                -- is_alive False, SIGTERM doesn't matter

        Since the normal case is the third one, we'll nicely ask our workers to
        quit with SIGTERM, then after some time force kill everything.

        However, on some systems we get the first case where even "kill -9"
        fails until the process fully registers with the OS, so we'll just
        do our best.

        Note: A more robust way would be just to pass SIGTERM then exit, and
        let the remaining workers commit suicide when they notice we died.
        This requires passing our PID to workers as an argument, and having
        workers periodically check on its parent.  See:
        http://stackoverflow.com/questions/2542610/python-daemon-doesnt-kill-its-kids
        We may also want to use this:
        http://pypi.python.org/pypi/python-daemon
        """
        self._shutdown = True
        if not self._shutdownWorkersNicely():
            self._shutdownWorkersForcefully()
        self._workers = {}

    def _shutdownWorkersNicely(self):
        """
        Ask workers to quit via SIGTERM and give them time to finish.
        Returns true if we think all the workers quit nicely.
        """
        no_problem_children = True
        for worker in self._workers.values():
            log.info("Stopping worker %s...", worker)
            if not worker.is_alive():
                no_problem_children = False  # Worker may be starting up.
            worker.terminate()

        # Give them some time to quit.
        # (This logic is built into Python 3.3 via Process.sentinel)
        for i in range(MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS):
            foundLivingWorker = False
            for p in self._workers.values():
                if p.is_alive():
                    foundLivingWorker = True
                    break
            if not foundLivingWorker:
                # All workers either quit or haven't fully started yet.
                return no_problem_children

            if i < MAX_SECONDS_TO_NICELY_SHUTDOWN_WORKERS - 1:
                sleep(1)  # Give them another second to finish up.

        return False  # Out of time.

    def _shutdownWorkersForcefully(self):
        """
        Continually run kill -9 on workers, but give up after a while.
        """
        log.warn("Forcefully killing worker processes...")
        # TODO: We don't need to keep killing workers who nicely changed from
        # is_alive to dead, or who we successfully kill then join here.
        # Currently we loop every time, trying to kill all every time.
        # This means "zenblah shutdown" will take 10 seconds instead of 5.
        for i in range(MAX_SECONDS_TO_FORCE_KILL_WORKERS):
            for worker in self._workers.values():
                try:
                    os.kill(worker.pid, signal.SIGKILL)
                    os.waitpid(worker.pid, os.WNOHANG)
                    worker.join()
                    log.info("Force killed worker pid %s", worker.pid)
                except OSError:
                    # It hasn't fully started, or it died, or we already
                    # force killed it. We'll try again but log it just in case.
                    log.info("Could not kill worker pid %s", worker.pid)

            if i < MAX_SECONDS_TO_FORCE_KILL_WORKERS - 1:
                sleep(1)  # Give them another second to finish up.

    def checkWorkers(self, *args):
        log.debug("checkWorkers method")
        if self._checking:
            log.debug("already checking")
            return
        try:
            self._checking = True
            log.debug(
                "checking workers: current %s, max %s",
                len(self._workers),
                self._maxWorkers,
            )
            renewed_workers = {}
            for worker_id in self._workers:
                if not self._workers[worker_id].is_alive():
                    # It's possible this worker hasn't fully registered with
                    # the OS and will soon start, but it's unlikely we'd be
                    # here that soon.
                    log.info(
                        "worker %s is dead. Starting worker again",
                        self._workers[worker_id],
                    )
                    renewed_workers[worker_id] = self._startWorker(worker_id)
            self._workers.update(renewed_workers)
        finally:
            self._checking = False

    def _startWorker(self, worker_id):
        workerName = worker_id
        if self._workerName:
            workerName = "%s %s" % (self._workerName, worker_id)
        log.warning("Starting worker %s", workerName)
        # if self._workerTarget is None, we just call
        # exec_worker with _workerCount + 1 as worker_id
        target = self._workerTarget
        target_kwargs = {}
        if self._workerTarget is None:
            target = exec_worker
            target_kwargs = {"worker_id": worker_id}
        p = multiprocessing.Process(
            target=target, name=workerName, kwargs=target_kwargs
        )
        p.daemon = True
        p.start()
        log.info("Started worker %s: current pid=%s", p, p.pid)
        return p
