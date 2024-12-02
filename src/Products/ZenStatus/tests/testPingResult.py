##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import math
import os.path

from Products.ZenStatus.nmap import PingResult
from Products.ZenTestCase.BaseTestCase import BaseTestCase

NO_TRACE = tuple()
NAN = float("nan")
testObjs = [
    {
        "ip": "10.175.210.231",
        "timestamp": None,
        "isUp": False,
        "rtt": NAN,
        "variance": NAN,
        "trace": NO_TRACE,
    },
    {
        "ip": "10.175.210.226",
        "timestamp": None,
        "isUp": False,
        "rtt": NAN,
        "variance": NAN,
        "trace": NO_TRACE,
    },
    {
        "ip": "10.175.211.23",
        "timestamp": None,
        "isUp": False,
        "rtt": NAN,
        "variance": NAN,
        "trace": NO_TRACE,
    },
    {
        "ip": "10.175.211.222",
        "timestamp": None,
        "isUp": False,
        "rtt": NAN,
        "variance": NAN,
        "trace": NO_TRACE,
    },
    {
        "ip": "10.175.211.134",
        "timestamp": None,
        "isUp": False,
        "rtt": NAN,
        "variance": NAN,
        "trace": NO_TRACE,
    },
    {
        "ip": "74.125.159.125",
        "timestamp": 1320675100,
        "isUp": True,
        "rtt": 39.186,
        "variance": 29.587,
        "trace": [
            ("10.87.209.1", 0.66),
            ("66.194.163.209", 1.51),
            ("66.192.241.70", 6.63),
            ("72.14.233.67", 6.56),
            ("72.14.237.217", 6.86),
            ("209.85.248.31", 38.68),
            ("209.85.254.2", 41.26),
            ("74.125.159.125", 38.68),
        ],
    },
    {
        "ip": "74.63.38.26",
        "timestamp": 1320675100,
        "isUp": True,
        "rtt": 45.718,
        "variance": 14.642,
        "trace": [
            ("10.87.209.1", 0.66),
            ("66.194.163.209", 1.51),
            ("66.192.250.154", 25.92),
            ("208.122.44.133", 233.37),
            ("208.122.44.202", 47.47),
            ("208.122.44.210", 47.48),
            ("74.63.38.26", 45.74),
        ],
    },
]


class TestPingResult(BaseTestCase):
    def setUp(self):
        # find the path to the test XML
        nmap_testfile = os.path.sep.join(
            [os.path.dirname(os.path.realpath(__file__)), "nmap_ping.xml"]
        )
        # parse the example nmap output
        input = open(nmap_testfile)
        result = PingResult.parseNmapXmlToDict(input)
        # hang it off self for tests to use
        self._result = result

    def testHostList(self):
        for o in testObjs:
            self.assertEqual(o["ip"] in self._result, True)

    def testTimestamp(self):
        for o in testObjs:
            hostResult = self._result[o["ip"]]
            msg = "parsed object[%s] did not match test object[%s]" % (
                hostResult,
                ["ip"],
            )
            self.assertEqual(hostResult.timestamp, o["timestamp"], msg)

    def testStatus(self):
        for o in testObjs:
            hostResult = self._result[o["ip"]]
            msg = "parsed object[%s] did not match test object[%s]" % (
                hostResult,
                ["ip"],
            )
            self.assertEqual(hostResult.isUp, o["isUp"], msg)

    def testRtt(self):
        for o in testObjs:
            hostResult = self._result[o["ip"]]
            msg = "parsed object[%s] did not match test object[%s]" % (
                hostResult,
                ["ip"],
            )
            if o["rtt"] >= 0:
                self.assertEqual(hostResult.rtt, o["rtt"], msg)
                self.assertEqual(hostResult.variance, o["variance"], msg)
            elif math.isnan(o["rtt"]):
                self.assertEqual(math.isnan(hostResult.rtt), True, msg)

    def testTraceRoute(self):
        for o in testObjs:
            hostResult = self._result[o["ip"]]
            msg = "parsed object[%s] did not match test object[%s]" % (
                hostResult,
                ["ip"],
            )
            self.assertEqual(len(hostResult.trace), len(o["trace"]), msg)
            for i, hop in enumerate(hostResult.trace):
                msg = (
                    "parsed object[%s] did not match test object[%s] : address"
                    % (hostResult, ["ip"])
                )
                self.assertEqual(hop.ip, o["trace"][i][0], msg)
                msg = (
                    "parsed object[%s] did not match test object[%s] : rtt"
                    % (hostResult, ["ip"])
                )
                self.assertEqual(hop.rtt, o["trace"][i][1], msg)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestPingResult))
    return suite
