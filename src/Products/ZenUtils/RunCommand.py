##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010-2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""RunCommand
Run an event command on the serviced host server.

  Example usage:

dcsh --collector=COLLECTOR_ID 'zencommand run'

  The actual command to run *MUST* be in quotes!
"""

from __future__ import print_function

import logging
import os
import signal
import subprocess
import sys

from .Utils import zenPath
from .ZenScriptBase import ZenScriptBase

log = logging.getLogger("zen.runCommand")


class CollectorStats:
    def __init__(self, id):
        self.id = id
        self.succeeded = False
        self.stdout = ""
        self.stderr = ""


class RunCommand(ZenScriptBase):
    def __init__(self):
        self.inputArgs = sys.argv[1:]
        configfile = zenPath("etc", "dcsh.conf")
        if os.path.exists(configfile):
            self.inputArgs.extend(["-C", configfile])

        ZenScriptBase.__init__(self, connect=True)

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option(
            "--collector",
            dest="collectorId",
            default="localhost",
            metavar="COLLECTOR_ID",
            help="Name of specific collector on which to run the command",
        )
        self.parser.add_option(
            "--timeout",
            dest="timeout",
            default=60,
            type="int",
            help="Kill the process after this many seconds.",
        )

    def run(self):
        collector = CollectorStats(self.options.collectorId)
        self._runCommandOnCollector(collector)
        self._report(collector)

    def _report(self, collector):
        header = (
            """
Collector=%s       StdOut/Stderr"""
            % collector.id
        )
        delimLen = 65
        print(header)
        print("-" * delimLen)

        print("%s %s" % (collector.stdout, collector.stderr))
        print("-" * delimLen)

    def _runCommandOnCollector(self, collector):
        def killTimedOutProc(signum, frame):
            log.error("Killing process id %s ...", proc.pid)
            try:
                os.kill(proc.pid, signal.SIGKILL)
            except OSError:
                pass

        remoteCommand = self.args[0]
        command = " ".join(
            [
                "zminion",
                "--minion-name",
                "zminion_" + collector.id,
                "run",
                "--",
                "'%s'" % remoteCommand,
            ]
        )

        log.debug(
            "Running command '%s' on collector %s", command, collector.id
        )
        proc = subprocess.Popen(  # noqa: S602
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        signal.signal(signal.SIGALRM, killTimedOutProc)
        signal.alarm(self.options.timeout)
        collector.stdout, collector.stderr = proc.communicate()
        proc.wait()
        signal.alarm(0)  # Disable the alarm


def main():
    RunCommand().run()
