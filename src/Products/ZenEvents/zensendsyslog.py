##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import socket
import time

from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.CmdBase import CmdBase

defaultInfile = zenPath("log", "origsyslog.log")
SYSLOG_PORT = socket.getservbyname("syslog", "udp")


class ZenSendSyslog(CmdBase):
    def __init__(self):
        CmdBase.__init__(self)
        self.host = socket.gethostbyname(self.options.host)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def run(self):
        self.log.info("sending messages to host %s", self.host)
        count = 0
        start = time.time()

        def linefilt(line):
            line = line.strip()
            return line and not line.startswith("#")

        lines = filter(linefilt, open(self.options.infile).readlines())
        rate = self.options.rate
        nextsec = time.time() + 0.9
        for line in lines:
            # self.log.debug(line)
            if count % rate == 0 and nextsec > time.time():
                while nextsec > time.time():
                    pass
                nextsec = time.time() + 0.9
            count += 1
            self.sock.sendto(line, (self.host, SYSLOG_PORT))
        sendtime = time.time() - start
        arate = count / sendtime
        self.log.info(
            "sent %d events in %.2f secs rate %.2f ev/sec",
            count,
            time.time() - start,
            arate,
        )

    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option(
            "--infile",
            dest="infile",
            default=defaultInfile,
            help="file from which to draw events",
        )

        self.parser.add_option(
            "--rate",
            dest="rate",
            type="int",
            default=80,
            help="events per sec to send",
        )

        self.parser.add_option(
            "-H",
            "--host",
            dest="host",
            default="localhost",
            help="host to send to",
        )


if __name__ == "__main__":
    sender = ZenSendSyslog()
    sender.run()
