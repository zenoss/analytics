##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from Products.DataCollector.plugins.zenoss.cmd.linux.ifconfig import parseDmesg
from Products.ZenTestCase.BaseTestCase import BaseTestCase


exampleLines = {
    100000000: [
        "tg3: eth0: Link is up at 100 Mbps, full duplex.",
        "[ 58.632984] eth0: link up, 100Mbps, full-duplex, lpa 0x45E1",
        "eth0: link up, 100Mbps, full-duplex, lpa 0x45E1",
        "eth0: Setting 100mbps full-duplex based on auto-negotiated "
        "partner ability 45e1.",
        "[   39.607974] eth0: link on 100 Mbps Full Duplex mode. ",
    ],
    1000000000: [
        "tg3: eth0: Link is up at 1000 Mbps, full duplex.",
        "0000:00:19.0: eth0: Link is Up 1000 Mbps Full Duplex, "
        "Flow Control: RX/TX",
    ],
}


class Object(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ParseDmesgTest(BaseTestCase):
    def runTest(self):
        eth0 = Object(interfaceName="eth0")
        relMap = Object(maps=[eth0])
        for expectedSpeed, lines in exampleLines.items():
            for line in lines:
                parseDmesg(line, relMap)
                self.assertEqual(expectedSpeed, eth0.speed)
                del eth0.speed


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ParseDmesgTest))
    return suite
