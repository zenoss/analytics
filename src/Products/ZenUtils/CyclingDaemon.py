##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import socket
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.Utils import getDefaultZopeUrl
from Products.ZenEvents import Event
from twisted.internet import reactor, defer

DEFAULT_MONITOR = "localhost"

class CyclingDaemon(ZCmdBase):

    def main_loop(self):
        raise NotImplementedError("Your daemon must define this method.")

    def run(self):
        reactor.callLater(0, self.runCycle)
        reactor.run()

    def finish(self, results=None):
        reactor.stop()

    def sendEvent(self, evt):
        """Send event to the system.
        """
        self.dmd.ZenEventManager.sendEvent(evt)

    def sendHeartbeat(self):
        """Send a heartbeat event for this monitor.
        """
        timeout = self.options.cycletime*3
        evt = Event.EventHeartbeat(self.options.monitor, self.name, timeout)
        self.sendEvent(evt)
        self.niceDoggie(self.options.cycletime)

    @defer.inlineCallbacks
    def runCycle(self):
        try:
            self.syncdb()
            yield self.main_loop()
            self.sendHeartbeat()
        except Exception as e:
            self.log.exception("Unexpected exception while running jobs")
        if not self.options.cycle:
            self.finish()
        reactor.callLater(self.options.cycletime, self.runCycle)

    def sigTerm(self, signum=None, frame=None):
        """
        Controlled shutdown of main loop on interrupt.
        """
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            self.finish()

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--cycletime',
            dest='cycletime', default=60, type="int",
            help="check events every cycletime seconds")
        self.parser.add_option(
            '--zopeurl', dest='zopeurl',
            default=getDefaultZopeUrl(),
            help="http path to the root of the zope server")
        self.parser.add_option("--monitor", dest="monitor",
            default=DEFAULT_MONITOR,
            help="Name of monitor instance to use for heartbeat "
                " events. Default is %s." % DEFAULT_MONITOR)
