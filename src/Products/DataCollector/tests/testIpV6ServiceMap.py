##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products.DataCollector.plugins.zenoss.snmp.IpV6ServiceMap import (
    IpV6ServiceMap,
)
from Products.ZenTestCase.BaseTestCase import BaseTestCase

log = logging.getLogger("zen.testcases")


class TestIpV6ServiceMap(BaseTestCase):
    def afterSetUp(self):
        super(TestIpV6ServiceMap, self).afterSetUp()
        self.serviceMap = IpV6ServiceMap()

    def test_extractAddressAndPort_oneIPV4(self):

        # Matches a specific IPV4 address and port
        oid = "4.100.209.56.18.2020"
        expected = [("100.209.56.18", 2020)]
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertEqual(expected, result)

    def test_extractAddressAndPort_oneIPV6(self):

        # Matches a specific IPV6 address and port
        oid = "16.32.1.50.239.162.33.251.20.50.0.0.0.0.0.0.1.2222"
        expected = [("2001:32ef:a221:fb14:3200::1", 2222)]
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertEqual(expected, result)

    def test_extractAddressAndPort_anyIPV4(self):

        # Port match against any IPV4 address
        oid = "4.0.0.0.0.1919"
        expected = [("0.0.0.0", 1919)]
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertEqual(expected, result)

    def test_extractAddressAndPort_anyIPV4IPV6(self):

        # Port match against any IPV4 and IPV6 address
        oid = "16.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.7979"
        expected = [("::", 7979), ("0.0.0.0", 7979)]
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertEqual(expected, result)

    def test_extractAddressAndPort_InvalidInput(self):
        expected = []

        # Empty field
        result = self.serviceMap._extractAddressAndPort("")
        self.assertEqual(expected, result)

        # Bad Data Type
        result = self.serviceMap._extractAddressAndPort(12345)
        self.assertEqual(expected, result)

        # Invalid characters
        result = self.serviceMap._extractAddressAndPort(
            "98789.&(&.(*&.&(*6.9KHBH.VKJY.F"
        )
        self.assertEqual(expected, result)
        result = self.serviceMap._extractAddressAndPort("4.10.AC.4F.19.C0C0")
        self.assertEqual(expected, result)

    def test_extractAddressAndPort_ImproperFormat(self):
        expected = []

        # Length mismatch
        data = (
            "4",
            "4.3453",
            "4.12.123.222.45.34.24.56.45.23.4.65.65.23.12.124.154.7574",
            "4.45.32",
            "4.213.34.83.43",
            "16.34.32.64.23.5764",
            "16.53.35.56.76.87.97.23.235.65.87.12.45.76.34.235.12.34.57.34.34.3423",
        )
        for oid in data:
            result = self.serviceMap._extractAddressAndPort(oid)
            self.assertEqual(expected, result)

        # Unsupported address type
        result = self.serviceMap._extractAddressAndPort(
            "8.233.34.45.67.235.54.34.23.6521"
        )
        self.assertEqual(expected, result)

        # Port exceeds boundaries 0x1 - 0xFFFF
        data = (
            "4.12.32.43.67.99999",
            "4.12.32.43.67.0",
        )
        for oid in data:
            result = self.serviceMap._extractAddressAndPort(oid)
            self.assertEqual(expected, result)

        # IP byte address exceeds boundaries 0xFF
        data = (
            "4.213.456.324.21.2345",
            "16.546.234.657.32.658.769.235.123.34.43.678.432.2.4.5.6.5634",
        )
        for oid in data:
            result = self.serviceMap._extractAddressAndPort(oid)
            self.assertEqual(expected, result)

    def test_ignore_localhost_ipv4(self):
        oid = ".1.3.6.1.2.1.6.20.1.4.1.4.127.0.0.1.25"
        expected = []
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertTrue(len(result) == 0)

    def test_ignore_localhost_ipv6(self):
        oid = ".1.3.6.1.2.1.6.20.1.4.2.16.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.1"
        expected = []
        result = self.serviceMap._extractAddressAndPort(oid)
        self.assertTrue(len(result) == 0)


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestIpV6ServiceMap))
    return suite
