##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.Nagios import Nagios
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from .BaseParsersTestCase import Object


class TestNagiosParser(BaseTestCase):
    def setUp(self):
        self.cmd = Object()
        deviceConfig = Object()
        deviceConfig.device = "localhost"
        self.cmd.deviceConfig = deviceConfig

        self.cmd.name = "testDataSource"
        self.cmd.parser = "Nagios"
        self.cmd.result = Object()
        self.cmd.result.exitCode = 2
        self.cmd.severity = 2
        self.cmd.command = "testNagiosPlugin"
        self.cmd.eventKey = "nagiosKey"
        self.cmd.eventClass = "/Cmd"
        self.cmd.component = "zencommand"
        self.parser = Nagios()
        self.results = ParsedResults()
        self.dpdata = dict(
            processName="someJob a b c",
            ignoreParams=False,
            alertOnRestart=True,
            failSeverity=3,
        )

    def testNagios2case1(self):
        p1 = Object()
        p1.id = "np1"
        p1.data = self.dpdata
        self.cmd.points = [p1]

        self.cmd.result.output = "OK plugin"
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 0)

    def testNagios2case2(self):
        p1 = Object()
        p1.id = "np1"
        p1.data = self.dpdata
        self.cmd.points = [p1]

        self.cmd.result.output = "OK plugin | np1=77;;;"
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 1)
        self.assertEquals(77.0, self.results.values[0][1])

    def testNagios3case3(self):
        p1 = Object()
        p1.id = "/"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "/boot"
        p2.data = self.dpdata

        p3 = Object()
        p3.id = "/home"
        p3.data = self.dpdata

        p4 = Object()
        p4.id = "/var/log"
        p4.data = self.dpdata

        self.cmd.points = [p1, p2, p3, p4]

        self.cmd.result.output = """DISK OK - free space: / 3326 MB (56%); | /=2643MB;5948;5958;0;5968
/boot 68 MB (69%);
/home 69357 MB (27%);
/var/log 819 MB (84%); | /boot=68MB;88;93;0;98
/home=69357MB;253404;253409;0;253414
/var/log=818MB;970;975;0;980"""

        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 4)
        self.assertEquals(2643.0, self.results.values[0][1])
        self.assertEquals(68.0, self.results.values[1][1])
        self.assertEquals(69357.0, self.results.values[2][1])
        self.assertEquals(818.0, self.results.values[3][1])

    def testNagios3edgeCase1(self):
        """
        Multi-line parsing, Nagios v3 style
        """
        p1 = Object()
        p1.id = "np1"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "np2"
        p2.data = self.dpdata

        self.cmd.points = [p1, p2]

        self.cmd.result.output = """OK plugin | np1=77;;;

My friendly junk
More stuff | np2=66;;;

np3=55;;;"""
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 2)
        self.assertEquals(77.0, self.results.values[0][1])
        self.assertEquals(66.0, self.results.values[1][1])

    def testNagios3edgeCase2(self):
        """
        performance data only in subsequent lines (after the first)
        """
        p1 = Object()
        p1.id = "np1"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "np2"
        p2.data = self.dpdata

        self.cmd.points = [p1, p2]

        self.cmd.result.output = """OK plugin

My friendly junk
More stuff |
np1=77;;;
np2=66;;;

np3=55;;;"""
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 2)
        self.assertEquals(77.0, self.results.values[0][1])
        self.assertEquals(66.0, self.results.values[1][1])

    def testNagios3edgeCase3(self):
        """
        No performance data
        """
        p1 = Object()
        p1.id = "np1"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "np2"
        p2.data = self.dpdata

        self.cmd.points = [p1, p2]

        self.cmd.result.output = """OK plugin

My friendly junk
More stuff
"""
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 0)

    def testNagios3edgeCase4(self):
        """
        Incorrect use of pipes.
        """
        p1 = Object()
        p1.id = "rta"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "pl"
        p2.data = self.dpdata

        self.cmd.points = [p1, p2]

        self.cmd.result.output = (
            "PING OK|LOSS=0 RTA=0.34 |"
            "rta=0.337000ms;180.000000;300.000000;0.000000 pl=0%;100;100;0\n"
        )
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 2)
        self.assertEquals(0.337, self.results.values[0][1])
        self.assertEquals(0.0, self.results.values[1][1])

    def testNagiosLabelScheme(self):
        """
        No really, Nagios plugin output labels are stunned. WTF???
        """
        p1 = Object()
        p1.id = "np 1"
        p1.data = self.dpdata

        p2 = Object()
        p2.id = "np 2"
        p2.data = self.dpdata

        p3 = Object()
        p3.id = "label with spaces in it"
        p3.data = self.dpdata

        self.cmd.points = [p1, p2, p3]

        self.cmd.result.output = """OK plugin
|
'np 1'=77.3;;;
'np 2'=77.3e-7;;;
'label with spaces in it'=12%;50;70;0;100
np2=66;;;
np2=66;;;
"""
        self.parser.processResults(self.cmd, self.results)
        self.assertEquals(len(self.results.values), 3)
        self.assertEquals(77.3, self.results.values[0][1])
        self.assertEquals(7.7300000000000005e-06, self.results.values[1][1])
        self.assertEquals(12.0, self.results.values[2][1])


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestNagiosParser))
    return suite
