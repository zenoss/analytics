##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json

from Products.ZenRRD.CommandParser import ParsedResults
from Products.ZenRRD.parsers.JSON import JSON
from Products.ZenTestCase.BaseTestCase import BaseTestCase

from .BaseParsersTestCase import Object


class TestJSONParser(BaseTestCase):
    def setUp(self):
        self.cmd = Object()
        deviceConfig = Object()
        deviceConfig.device = "localhost"
        self.cmd.deviceConfig = deviceConfig

        self.cmd.name = "testDataSource"
        self.cmd.parser = "JSON"
        self.cmd.result = Object()
        self.cmd.result.exitCode = 0
        self.cmd.severity = 2
        self.cmd.eventKey = "testEventKey"
        self.cmd.eventClass = "/Cmd"
        self.cmd.command = "testJSONCommand"
        self.cmd.points = []
        self.parser = JSON()
        self.results = ParsedResults()

    def test_json_parse_error(self):
        self.cmd.result.output = "This isn't valid JSON data."
        self.parser.processResults(self.cmd, self.results)

        # No values should be returned for invalid JSON output.
        self.assertEquals(len(self.results.values), 0)

        # A single event should be returned for invalid JSON output.
        self.assertEquals(len(self.results.events), 1)

        event = self.results.events[0]

        self.assertEquals(event["severity"], self.cmd.severity)
        self.assertEquals(event["summary"], "error parsing command output")
        self.assertEquals(event["eventKey"], self.cmd.eventKey)
        self.assertEquals(event["eventClass"], self.cmd.eventClass)
        self.assertEquals(event["command_output"], self.cmd.result.output)
        self.assertTrue("exception" in event)

    def test_device_result(self):
        self.cmd.result.output = json.dumps(
            {
                "values": {
                    "": {
                        "value1": 1.0,
                        "value2": 2.0,
                    },
                },
                "events": [
                    {
                        "summary": "test summary",
                        "severity": 2,
                    },
                    {
                        "summary": "another summary",
                        "severity": 3,
                    },
                ],
            }
        )

        p1 = Object()
        p1.id = "value1"
        p1.component = ""

        p2 = Object()
        p2.id = "value2"
        p2.component = ""

        self.cmd.points = [p1, p2]

        self.parser.processResults(self.cmd, self.results)

        self.assertEquals(len(self.results.values), 2)

        value1 = self.results.values[0]
        self.assertEquals(value1[0].component, "")
        self.assertEquals(value1[0].id, "value1")
        self.assertEquals(value1[1], 1.0)

        value2 = self.results.values[1]
        self.assertEquals(value2[0].component, "")
        self.assertEquals(value2[0].id, "value2")
        self.assertEquals(value2[1], 2.0)

        self.assertEquals(len(self.results.events), 2)

    def test_component_result(self):
        self.cmd.result.output = json.dumps(
            {
                "values": {
                    "component1": {
                        "value1": 1.0,
                        "value2": 2.0,
                    },
                    "component2": {
                        "value1": 1.1,
                        "value2": 2.2,
                    },
                }
            }
        )

        p1_1 = Object()
        p1_1.id = "value1"
        p1_1.component = "component1"

        p1_2 = Object()
        p1_2.id = "value2"
        p1_2.component = "component1"

        p2_1 = Object()
        p2_1.id = "value1"
        p2_1.component = "component2"

        p2_2 = Object()
        p2_2.id = "value2"
        p2_2.component = "component2"

        self.cmd.points = [p1_1, p1_2, p2_1, p2_2]

        self.parser.processResults(self.cmd, self.results)

        self.assertEquals(len(self.results.values), 4)

        value1_1 = self.results.values[0]
        self.assertEquals(value1_1[0].component, "component1")
        self.assertEquals(value1_1[0].id, "value1")
        self.assertEquals(value1_1[1], 1.0)

        value1_2 = self.results.values[1]
        self.assertEquals(value1_2[0].component, "component1")
        self.assertEquals(value1_2[0].id, "value2")
        self.assertEquals(value1_2[1], 2.0)

        value2_1 = self.results.values[2]
        self.assertEquals(value2_1[0].component, "component2")
        self.assertEquals(value2_1[0].id, "value1")
        self.assertEquals(value2_1[1], 1.1)

        value2_2 = self.results.values[3]
        self.assertEquals(value2_2[0].component, "component2")
        self.assertEquals(value2_2[0].id, "value2")
        self.assertEquals(value2_2[1], 2.2)

        self.assertEquals(len(self.results.events), 0)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestJSONParser))
    return suite
