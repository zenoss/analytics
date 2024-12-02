##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.Cacti import Cacti
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from .BaseParsersTestCase import Object


class TestCacti(BaseTestCase):
    def setUp(self):
        self.parser = Cacti()

    def testCacti(self):
        deviceConfig = Object()
        deviceConfig.device = "localhost"
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        p1 = Object()
        p1.id = "cacti_single_result"
        p1.data = dict(
            processName="someJob a b c",
            ignoreParams=False,
            alertOnRestart=True,
            failSeverity=3,
        )
        cmd.points = [p1]
        cmd.result = Object()
        cmd.result.output = "77"
        cmd.result.exitCode = 2
        cmd.severity = 2
        cmd.command = "testCactiPlugin"
        cmd.name = "testCactiPlugin"
        cmd.eventKey = "cactiKey"
        cmd.eventClass = "/Cmd"
        cmd.component = "zencommand"
        results = ParsedResults()
        self.parser.processResults(cmd, results)
        self.assertEquals(len(results.values), 1)
        self.assertEquals(77, int(results.values[0][1]))

        # Now test multiple data points
        p2 = Object()
        p2.id = "cacti_multi_result"
        p2.data = dict(
            processName="someJob a b c",
            ignoreParams=False,
            alertOnRestart=True,
            failSeverity=3,
        )
        cmd.points.append(p2)
        cmd.result.output = (
            "cacti_single_result:77 cacti_multi_result: 4.03E02"
        )
        results = ParsedResults()
        self.parser.processResults(cmd, results)
        self.assertEquals(len(results.values), 2)
        values = map(lambda x: x[1], results.values)
        self.assertTrue(77.0 in values)
        self.assertTrue(403.0 in values)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestCacti))
    return suite
