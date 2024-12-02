#!/usr/bin/env python
##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """zentestsyslogrules
Apply the zensyslog regexes against messages captured by zensyslog
(default filename: $ZENHOME/log/origsyslog.log) and report on the
frequency of each message.
This allows one to test the effectiveness of the drop filtering.
"""

from Products.ZenEvents.SyslogProcessing import SyslogProcessor
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenUtils.Utils import zenPath

defaultInfile = zenPath("log", "origsyslog.log")

# The format of the capture syslog message is:
# timestamp timestamp ip_address: message
#Nov 30 13:45:03 Nov 30 2009 13:43:49 10.10.10.62 : %ASA-7-609001: Built local-host outside:10.10.10.10
# We just want the message
ORID_SYSLOG_METADATA_END_POS = 53


class ZenTestSyslogRules(CmdBase):

    def __init__(self):
        CmdBase.__init__(self)
        self.processor = SyslogProcessor(self.sendEvent,
                    self.options.minpriority, False,
                    "localhost", 2)
        self.keptEvent = False
        self.totalSent = 0

    def sendEvent(self, evt, *args, **kwargs):
        self.keptEvent = True
        self.totalSent += 1
  
    def getSyslogMsg(self, line):
        # Throw out captured meta-data
        return line[ORID_SYSLOG_METADATA_END_POS:-1]

    def run(self):
        # Apply the regex rules against all captured syslog messages
        totalEvents = 0
        counts= {}
        for line in open(self.options.infile):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            totalEvents += 1
            self.keptEvent = False
            self.processor.process(line, "127.0.0.1", "localhost", None)
            if self.keptEvent:
                key = self.getSyslogMsg(line)
                counts.setdefault(key, 0)
                counts[key] += 1

        # Print the output sorted by the number of times each message
        # has occurred in the original input
        for key, count in sorted(counts.items(), key=lambda x: x[1]):
            print "%d %s" % (count, key)
        droppedCount = totalEvents - self.totalSent
        droppedPct = 0
        if totalEvents:
            droppedPct = droppedCount * 100.0 / totalEvents
        self.log.info("Test event stats: dropped=%d sent=%d total=%d dropped_pct=%.1f",
                      droppedCount, self.totalSent, totalEvents, droppedPct)
    
    def buildOptions(self):
        CmdBase.buildOptions(self)
        self.parser.add_option('--infile',
            dest='infile', default=defaultInfile,
            help="File containing captured syslog events.")
        self.parser.add_option('--minpriority', dest='minpriority',
            default=6, type='int',
            help='Minimum priority message that zensyslog will accept')

if __name__ == "__main__":
    sender = ZenTestSyslogRules()
    try:
        sender.run()
    except (IOError, KeyboardInterrupt): pass
