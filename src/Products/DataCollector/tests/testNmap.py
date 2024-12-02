##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging

from Products.DataCollector.plugins.zenoss.nmap.IpServiceMap import (
    IpServiceMap,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class FakeDevice:
    def __init__(self, id):
        self.id = id


def dumpRelMap(relmap):
    """
    Display the contents returned from a modeler
    """
    for om in relmap:
        dumpObjectMapData(om)


def dumpObjectMapData(om):
    """
    I'm sure that 'Om' is not a reference to Terry Pratchet and
    the god of the same name.  Really.
    Anyway, this is a chance to view the mind of a small god.... :)
    """
    for attr in dir(om):
        obj = getattr(om, attr)
        if not attr.startswith("_") and not hasattr(obj, "__call__"):
            print("%s = %s" % (attr, obj))


class TestIpServiceMap(BaseTestCase):
    def afterSetUp(self):
        super(TestIpServiceMap, self).afterSetUp()

        self.device = FakeDevice("testdevice")

    def checkResults(self, omMap, parsed_data):
        for port_obj in omMap:
            self.assert_(port_obj.id in parsed_data)
            for attr in parsed_data[port_obj.id].keys():
                self.assertEquals(
                    getattr(port_obj, attr), parsed_data[port_obj.id][attr]
                )

            # We should only see the ports once
            del parsed_data[port_obj.id]

        self.assertEquals(len(parsed_data), 0)

    def testNmapv5GrepStyle(self):
        # nmap -p1-1024 -sT --open -oG - 192.168.10.10
        results = """# Nmap 5.10BETA2 scan initiated Tue Feb 16 06:02:37 2010 as: nmap -p1-1024 -sT --open -oG - 192.168.10.10
Host: 192.168.10.10 () Status: Up
Host: 192.168.10.10 () Ports: 22/open/tcp//ssh///, 80/open/tcp//http///, 199/open/tcp//smux///, 443/open/tcp//https/// Ignored State: closed (1020)
# Nmap done at Tue Feb 16 06:02:37 2010 -- 1 IP address (1 host up) scanned in 0.07 seconds
"""

        parsed_data = {
            "tcp_00022": {"port": 22, "ipaddresses": ["0.0.0.0"]},
            "tcp_00080": {"port": 80, "ipaddresses": ["0.0.0.0"]},
            "tcp_00199": {"port": 199, "ipaddresses": ["0.0.0.0"]},
            "tcp_00443": {"port": 443, "ipaddresses": ["0.0.0.0"]},
        }

        omMap = IpServiceMap().process(self.device, results, log)
        self.checkResults(omMap, parsed_data)

    def testNmapv5HumanStyle(self):
        results = """Starting Nmap 5.00 ( http://nmap.org ) at 2010-01-18 16:11 EST
Interesting ports on kells-cent5-32-1.zenoss.loc (10.175.211.24):
Not shown: 1021 closed ports
PORT    STATE SERVICE
22/tcp  open  ssh
111/tcp open  rpcbind
607/tcp open  nqs

Nmap done: 1 IP address (1 host up) scanned in 0.13 seconds
"""

        parsed_data = {
            "tcp_00022": {"port": 22, "ipaddresses": ["0.0.0.0"]},
            "tcp_00111": {"port": 111, "ipaddresses": ["0.0.0.0"]},
            "tcp_00607": {"port": 607, "ipaddresses": ["0.0.0.0"]},
        }

        omMap = IpServiceMap().process(self.device, results, log)
        self.checkResults(omMap, parsed_data)

    def testNmapv5GrepStyle2(self):
        results = """# Nmap 5.00 scan initiated Mon Jan 18 16:27:57 2010 as: /opt/zenoss/libexec/nmap -p 1-1024 -sT --open -oG - 10.175.211.24 
Host: 10.175.211.24 (kells-cent5-32-1.zenoss.loc)       Ports: 22/open/tcp//ssh///, 111/open/tcp//rpcbind///, 607/open/tcp//nqs///Ignored State: closed (1021)
# Nmap done at Mon Jan 18 16:27:57 2010 -- 1 IP address (1 host up) scanned in 0.21 seconds
"""

        parsed_data = {
            "tcp_00022": {"port": 22, "ipaddresses": ["0.0.0.0"]},
            "tcp_00111": {"port": 111, "ipaddresses": ["0.0.0.0"]},
            "tcp_00607": {"port": 607, "ipaddresses": ["0.0.0.0"]},
        }

        omMap = IpServiceMap().process(self.device, results, log)
        self.checkResults(omMap, parsed_data)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestIpServiceMap))
    return suite
