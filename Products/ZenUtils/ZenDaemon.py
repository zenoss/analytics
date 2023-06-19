##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import os
import pwd
import re
import signal
import socket
import sys

from platform import system
from urllib import getproxies

from twisted.internet import defer, reactor
from twisted.logger import globalLogBeginner
from twisted.python import log as twisted_log

from Products.ZenMessaging.audit import audit
from Products.Zuul.utils import safe_hasattr as hasattr

from .CmdBase import CmdBase
from .dumpthreads import dump_threads
from .path import binPath, zenPath
from .Utils import HtmlFormatter, setLogLevel
from .Watchdog import Reporter

# Daemon creation code below based on Recipe by Chad J. Schroeder
# File mode creation mask of the daemon.
UMASK = 0o022

# Default working directory for the daemon.
WORKDIR = "/"

# only close stdin/out/err
MAXFD = 3

# The standard I/O file descriptors are redirected to /dev/null by default.
REDIRECT_TO = os.devnull if hasattr(os, "devnull") else "/dev/null"


class ZenDaemon(CmdBase):
    """Base class for creating daemons."""

    pidfile = None

    def __init__(self, noopts=0, keeproot=False):
        """
        Initializer that takes care of basic daemon options.
        Creates a PID file.
        """
        super(ZenDaemon, self).__init__(noopts)
        self.pidfile = None
        self.keeproot = keeproot
        self.reporter = None
        self.fqdn = socket.getfqdn()

        reactor.addSystemEventTrigger("before", "shutdown", self.sigTerm)
        if not noopts:
            if self.options.daemon:
                self.changeUser()
                self.becomeDaemon()
            if (
                self.options.pidfile
                or self.options.daemon
                or self.options.watchdogPath
            ):
                try:
                    self.writePidFile()
                except OSError:
                    raise SystemExit(
                        "ERROR: unable to open PID file %s"
                        % (self.pidfile or "(unknown)",)
                    )
        if self.options.watchdog and not self.options.watchdogPath:
            self.becomeWatchdog()
        self.audit("Start")

    def audit(self, action):
        processName = re.sub(r"^.*/", "", sys.argv[0])
        daemon = re.sub(".py$", "", processName)
        audit("Shell.Daemon." + action, daemon=daemon)

    def convertSocketOption(self, optString):
        """
        Given a socket option string (eg 'so_rcvbufforce=1') convert
        to a C-friendly command-line option for passing to zensocket.
        """
        optString = optString.upper()
        if "=" not in optString:  # Assume boolean
            flag = optString
            value = 1
        else:
            flag, value = optString.split("=", 1)
            try:
                value = int(value)
            except ValueError:
                self.log.warn(
                    "The value %s for flag %s cound not be converted",
                    value,
                    flag,
                )
                return None
        # Check to see if we can find the option
        if flag not in dir(socket):
            self.log.warn("The flag %s is not a valid socket option", flag)
            return None
        numericFlag = getattr(socket, flag)
        return "--socketOpt=%s:%s" % (numericFlag, value)

    def openPrivilegedPort(self, *address):
        """Execute under zensocket, providing the args to zensocket."""
        socketOptions = []
        for optString in set(self.options.socketOption):
            arg = self.convertSocketOption(optString)
            if arg:
                socketOptions.append(arg)
        zensocket = binPath("zensocket")
        cmd = (
            [zensocket, zensocket]
            + list(address)
            + socketOptions
            + ["--", sys.executable]
            + sys.argv
            + ["--useFileDescriptor=$privilegedSocket"]
        )
        self.log.debug(cmd)
        os.execlp(*cmd)

    def writePidFile(self):
        """Write the PID file to disk."""
        pidfile = getattr(self.options, "pidfile", "")
        if pidfile:
            myname = pidfile
        else:
            myname = sys.argv[0].split(os.sep)[-1]
            if myname.endswith(".py"):
                myname = myname[:-3]
            monitor = getattr(self.options, "monitor", "localhost")
            myname = "%s-%s.pid" % (myname, monitor)
        if self.options.watchdog and not self.options.watchdogPath:
            self.pidfile = zenPath("var", "watchdog-%s" % myname)
        else:
            self.pidfile = zenPath("var", myname)
        fp = open(self.pidfile, "w")
        mypid = str(os.getpid())
        fp.write(mypid)
        fp.close()
        self.log.info("current pid: %s", mypid)

    @property
    def logname(self):
        return getattr(self, "mname", self.__class__.__name__)

    def setupLogging(self):
        """Create formating for log entries and set default log level."""
        # Initialize twisted logging to go nowhere.
        globalLogBeginner.beginLoggingTo(
            [lambda x: None], redirectStandardIO=False, discardBuffer=True
        )

        # Setup python logging module
        rootLog = logging.getLogger()
        rootLog.setLevel(logging.WARN)
        zenLog = logging.getLogger("zen")
        zenLog.setLevel(self.options.logseverity)

        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )

        if self.options.logfileonly:
            # clear out existing handlers
            hdlrs = rootLog.handlers
            for hdlr in hdlrs:
                rootLog.removeHandler(hdlr)

        if (
            self.options.watchdogPath
            or self.options.daemon
            or self.options.duallog
            or self.options.logfileonly
        ):
            logdir = self.checkLogpath() or zenPath("log")

            handler = logging.handlers.RotatingFileHandler(
                filename=os.path.join(logdir, "%s.log" % self.logname.lower()),
                maxBytes=self.options.maxLogKiloBytes * 1024,
                backupCount=self.options.maxBackupLogs,
            )
            handler.setFormatter(formatter)
            rootLog.addHandler(handler)

        if not (
            self.options.watchdogPath
            or self.options.daemon
            or self.options.logfileonly
        ):
            # We are logging to the console
            # Find the stream handler and make it match our desired log level
            if self.options.weblog:
                formatter = HtmlFormatter()

            if not rootLog.handlers:
                # Add a stream handler to stream to the console
                consoleHandler = logging.StreamHandler(sys.stderr)
                rootLog.addHandler(consoleHandler)

            for handler in (
                h
                for h in rootLog.handlers
                if isinstance(h, logging.StreamHandler)
            ):
                handler.setFormatter(formatter)

        self.log = logging.getLogger("zen.%s" % self.logname)

        # Allow the user to dynamically lower and raise the logging
        # level without restarts.
        try:
            signal.signal(signal.SIGUSR1, self.sighandler_USR1)
        except ValueError:
            # If we get called multiple times, this will generate an exception:
            # ValueError: signal only works in main thread
            # Ignore it as we've already set up the signal handler.
            pass

    def sighandler_USR1(self, signum, frame):
        """
        Switch to debug level if signaled by the user, and to
        default when signaled again.
        """

        def getTwistedLogger():
            loggerName = "zen.%s.twisted" % self.logname
            return twisted_log.PythonLoggingObserver(loggerName=loggerName)

        log = logging.getLogger("zen")
        currentLevel = log.getEffectiveLevel()
        if currentLevel == logging.DEBUG:
            if self.options.logseverity == logging.DEBUG:
                return
            setLogLevel(self.options.logseverity, "zen")
            log.info(
                "Restoring logging level back to %s (%d)",
                logging.getLevelName(self.options.logseverity) or "unknown",
                self.options.logseverity,
            )
            try:
                defer.setDebugging(False)
                getTwistedLogger().stop()
            except ValueError:  # Twisted logging is somewhat broken
                log.info(
                    "Unable to remove Twisted logger -- "
                    "expect Twisted logging to continue."
                )
        else:
            setLogLevel(logging.DEBUG, "zen")
            log.info("Setting logging level to DEBUG")
            defer.setDebugging(True)
            getTwistedLogger().start()
        dump_threads(signum, frame)
        self._sigUSR1_called(signum, frame)
        self.audit("Debug")

    def _sigUSR1_called(self, signum, frame):
        pass

    def changeUser(self):
        """Switch identity to the appropriate Unix user."""
        if not self.keeproot:
            try:
                cname = pwd.getpwuid(os.getuid())[0]
                pwrec = pwd.getpwnam(self.options.uid)
                os.setuid(pwrec.pw_uid)
                os.environ["HOME"] = pwrec.pw_dir
            except (KeyError, OSError):
                print(
                    "WARN: user:%s not found running as:%s"
                    % (self.options.uid, cname),
                    file=sys.stderr,
                )

    def becomeDaemon(self):
        """Code below comes from the excellent recipe by Chad J. Schroeder."""
        # Workaround for http://bugs.python.org/issue9405 on Mac OS X
        if system() == "Darwin":
            getproxies()
        try:
            pid = os.fork()
        except OSError as e:
            raise Exception("%s [%d]" % (e.strerror, e.errno))

        if pid == 0:  # The first child.
            os.setsid()
            try:
                pid = os.fork()  # Fork a second child.
            except OSError as e:
                raise Exception("%s [%d]" % (e.strerror, e.errno))

            if pid == 0:  # The second child.
                os.chdir(WORKDIR)
                os.umask(UMASK)
            else:
                # Exit parent (the first child) of the second child.
                os._exit(0)
        else:
            os._exit(0)  # Exit parent of the first child.

        # Iterate through and close all stdin/out/err
        for fd in range(0, MAXFD):
            try:
                os.close(fd)
            except OSError:  # ERROR, fd wasn't open to begin with (ignored)
                pass

        os.open(REDIRECT_TO, os.O_RDWR)  # standard input (0)
        # Duplicate standard input to standard output and standard error.
        os.dup2(0, 1)  # standard output (1)
        os.dup2(0, 2)  # standard error (2)

    def sigTerm(self, signum=None, frame=None):
        """Signal handler for the SIGTERM signal."""
        from Products.ZenUtils.Utils import unused

        unused(signum, frame)
        stop = getattr(self, "stop", None)
        if callable(stop):
            stop()
        if self.pidfile and os.path.exists(self.pidfile):
            self.log.info("Deleting PID file %s ...", self.pidfile)
            os.remove(self.pidfile)
        self.log.info("received signal to shut down")
        self.audit("Stop")

    def watchdogCycleTime(self):
        """
        Return our cycle time (in minutes).

        @return: cycle time
        @rtype: integer
        """
        # time between child reports: default to 2x the default cycle time
        default = 1200
        cycleTime = getattr(self.options, "cycleTime", default)
        if not cycleTime:
            cycleTime = default
        return cycleTime

    def watchdogStartTimeout(self):
        """
        Return our watchdog start timeout (in minutes).

        @return: start timeout
        @rtype: integer
        """
        # Default start timeout should be cycle time plus a couple of minutes
        default = self.watchdogCycleTime() + 120
        startTimeout = getattr(self.options, "starttimeout", default)
        if not startTimeout:
            startTimeout = default
        return startTimeout

    def watchdogMaxRestartTime(self):
        """
        Return our watchdog max restart time (in minutes).

        @return: maximum restart time
        @rtype: integer
        """
        default = 600
        maxTime = getattr(self.options, "maxRestartTime", default)
        if not maxTime:
            maxTime = default
        return default

    def becomeWatchdog(self):
        """Watch the specified daemon and restart it if necessary."""
        from Products.ZenUtils.Watchdog import Watcher, log

        log.setLevel(self.options.logseverity)
        cmd = sys.argv[:]
        if "--watchdog" in cmd:
            cmd.remove("--watchdog")
        if "--daemon" in cmd:
            cmd.remove("--daemon")

        socketPath = "%s/.%s-watchdog-%d" % (
            zenPath("var"),
            self.__class__.__name__,
            os.getpid(),
        )

        cycleTime = self.watchdogCycleTime()
        startTimeout = self.watchdogStartTimeout()
        maxTime = self.watchdogMaxRestartTime()
        self.log.debug(
            "Watchdog cycleTime=%d startTimeout=%d maxTime=%d",
            cycleTime,
            startTimeout,
            maxTime,
        )

        watchdog = Watcher(socketPath, cmd, startTimeout, cycleTime, maxTime)
        watchdog.run()
        sys.exit(0)

    def niceDoggie(self, timeout):
        # defer creation of the reporter until we know we're not going
        # through zensocket or other startup that results in closing
        # this socket
        if not self.reporter and self.options.watchdogPath:
            self.reporter = Reporter(self.options.watchdogPath)
        if self.reporter:
            self.reporter.niceDoggie(timeout)

    def buildOptions(self):
        super(ZenDaemon, self).buildOptions()
        self.parser.add_option(
            "--uid",
            dest="uid",
            default="zenoss",
            help="User to become when running; default %default",
        )
        self.parser.add_option(
            "-c",
            "--cycle",
            dest="cycle",
            action="store_true",
            default=False,
            help="Cycle continuously on cycleInterval from Zope",
        )
        self.parser.add_option(
            "-D",
            "--daemon",
            default=False,
            dest="daemon",
            action="store_true",
            help="Launch into the background",
        )
        self.parser.add_option(
            "--duallog",
            default=False,
            dest="duallog",
            action="store_true",
            help="Log to console and log file",
        )
        self.parser.add_option(
            "--logfileonly",
            default=False,
            dest="logfileonly",
            action="store_true",
            help="Log to log file and not console",
        )
        self.parser.add_option(
            "--weblog",
            default=False,
            dest="weblog",
            action="store_true",
            help="output log info in HTML table format",
        )
        self.parser.add_option(
            "--watchdog",
            default=False,
            dest="watchdog",
            action="store_true",
            help="Run under a supervisor which will restart it",
        )
        self.parser.add_option(
            "--watchdogPath",
            default=None,
            dest="watchdogPath",
            help="The path to the watchdog reporting socket",
        )
        self.parser.add_option(
            "--starttimeout",
            dest="starttimeout",
            type="int",
            help="Wait seconds for initial heartbeat",
        )
        self.parser.add_option(
            "--socketOption",
            dest="socketOption",
            default=[],
            action="append",
            help="Set listener socket options. "
            "For option details: man 7 socket",
        )
        self.parser.add_option(
            "--heartbeattimeout",
            dest="heartbeatTimeout",
            type="int",
            default=getattr(self, "heartbeatTimeout", 900),
            help="Set a heartbeat timeout in seconds for a daemon; "
            "default %default",
        )
        self.parser.add_option(
            "--pidfile",
            dest="pidfile",
            default="",
            help="pidfile to save a pid number of a process",
        )
