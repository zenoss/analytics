##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import atexit
import errno
import fcntl
import logging
import os

from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.pid")


def _add_pid_suffix(v):
    if not v.endswith(".pid"):
        if not os.path.basename(v):
            raise ValueError("no filename for pid file given")
        return v + ".pid"
    return v


def add_pidfile_arguments(parser):
    filename = "-".join(parser.prog.split(" ")[:-1]) + ".pid"
    dirname = os.path.join(zenPath("var"), "run")
    parser.add_argument(
        "--pidfile",
        default=os.path.join(dirname, filename),
        type=_add_pid_suffix,
        help="Pathname of the PID file.  If a directory path is not "
        "specified, the pidfile is save to {}".format(dirname),
    )


class pidfile(object):
    """
    Write a file containing the current process's PID.

    The context manager yields the PID value to the caller.
    """

    def __init__(self, config):
        pidfile = config["pidfile"]
        filename = os.path.basename(pidfile)
        dirname = os.path.dirname(pidfile)
        if not os.path.isdir(dirname):
            if not dirname:
                dirname = os.path.join(zenPath("var"), "run")
            else:
                raise RuntimeError(
                    "not a directory  direcory={}".format(dirname)
                )
        self._dirname = dirname
        self._filename = filename
        self.pathname = os.path.join(self._dirname, self._filename)

    def __enter__(self):
        self.create()
        return self

    def __exit__(self, exc_type=None, exc_value=None, exc_tb=None):
        self.close()

    def read(self):
        with open(self.pathname, "r") as fp:
            return _read_pidfile(fp)

    def create(self):
        atexit.register(self.close)
        self.pid = os.getpid()
        self.fp = open(self.pathname, "a+")
        try:
            _flock(self.fp.fileno())
        except IOError as ex:
            raise RuntimeError(
                "pidfile already locked  pidfile={} error={}".format(
                    self.pathname, ex
                )
            )
        oldpid = _read_pidfile(self.fp)
        if oldpid is not None and pid_exists(oldpid):
            raise RuntimeError("PID is still running  pid={}".format(oldpid))
        self.fp.seek(0)
        self.fp.truncate()
        self.fp.write("%d\n" % self.pid)
        self.fp.flush()
        self.fp.seek(0)

    def close(self):
        if not self.fp:
            return
        try:
            self.fp.close()
            self.fp = None  # so subsequent calls to `close` exit early
        except IOError as ex:
            if ex.errno != errno.EBADF:
                raise
        finally:
            if os.path.isfile(self.pathname):
                os.remove(self.pathname)


def pid_exists(pid):
    try:
        os.kill(pid, 0)
    except OSError as ex:
        if ex.errno == errno.ESRCH:
            # This pid has no matching process
            return False
    return True


def _read_pidfile(fp):
    fp.seek(0)
    pid_str = fp.read(16).split("\n", 1)[0].strip()
    if not pid_str:
        return None
    return int(pid_str)


def _flock(fileno):
    fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)
