##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import os
import signal
import sys

from .app import pidfile


class Debug(object):
    @classmethod
    def from_args(cls, args):
        return cls(args.pidfile)

    def __init__(self, pidfile):
        self.pidfile = pidfile

    def run(self):
        pf = pidfile({"pidfile": self.pidfile})
        try:
            pid = pf.read()
            try:
                os.kill(pid, signal.SIGUSR1)
                print(
                    "Signaled {} to toggle debug mode".format(
                        self.pidfile.split(".")[0]
                        .split("/")[-1]
                        .replace("-", " ")
                    )
                )
            except OSError as ex:
                print("{} ({})".format(ex, pid), file=sys.stderr)
                sys.exit(1)
        except IOError as ex:
            print("{}".format(ex), file=sys.stderr)
            sys.exit(1)
