##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.Auto import Auto

from .BaseParsersTestCase import Object
from .testCacti import TestCacti
from .testNagiosParser import TestNagiosParser


class TestAutoParser(TestNagiosParser, TestCacti):
    def setUp(self):
        self.cmd = Object()
        deviceConfig = Object()
        deviceConfig.device = "localhost"
        self.cmd.deviceConfig = deviceConfig

        self.cmd.name = "testDataSource"
        self.cmd.parser = "Auto"
        self.cmd.result = Object()
        self.cmd.result.exitCode = 2
        self.cmd.severity = 2
        self.cmd.command = "testAutoPlugin"
        self.cmd.eventKey = "AutoKey"
        self.cmd.eventClass = "/Cmd"
        self.cmd.component = "zencommand"
        self.parser = Auto()
        self.results = ParsedResults()
        self.dpdata = dict(
            processName="someJob a b c",
            ignoreParams=False,
            alertOnRestart=True,
            failSeverity=3,
        )

    def testNagiosAutoCaseApache(self):
        self.cmd.points = []

        slotDNSLookup = Object()
        slotDNSLookup.id = "slotDNSLookup"
        slotDNSLookup.data = self.dpdata
        self.cmd.points.append(slotDNSLookup)

        totalAccesses = Object()
        totalAccesses.id = "totalAccesses"
        totalAccesses.data = self.dpdata
        self.cmd.points.append(totalAccesses)

        slotReadingRequest = Object()
        slotReadingRequest.id = "slotReadingRequest"
        slotReadingRequest.data = self.dpdata
        self.cmd.points.append(slotReadingRequest)

        busyServers = Object()
        busyServers.id = "busyServers"
        busyServers.data = self.dpdata
        self.cmd.points.append(busyServers)

        self.cmd.result.output = (
            "STATUS OK|"
            "slotDNSLookup=0 "
            "totalAccesses=38 "
            "slotReadingRequest=0 "
            "totalKBytes=15 "
            "busyServers=1 "
            "slotKeepAlive=0 "
            "slotGracefullyFinishing=0 "
            "bytesPerReq=404.211 "
            "cpuLoad=.000142755 "
            "bytesPerSec=2.19272 "
            "slotLogging=0 "
            "slotSendingReply=1 "
            "slotStartingUp=0 "
            "reqPerSec=.0054247 "
            "slotWaiting=7 "
            "slotOpen=248 "
            "idleServers=7"
        )
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(4, len(self.results.values))


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestAutoParser))
    return suite
