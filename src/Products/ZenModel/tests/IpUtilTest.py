##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


#
#

__doc__="""IpUtil unit tests

Tests for IP calculation/conversion routines.

$Id: IpUtilTest.py,v 1.1 2002/06/05 14:38:20 alex Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

import unittest
from Confmon import IpUtil
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest

class IpUtilTest(ZenModelBaseTest):

    def testCheckBadIpDot(self):
        '''check to see that checkip raises an error when
        fed input consisting of a single dot'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.checkip,
            '.')

    def testCheckBadIpText(self):
        '''check to see that checkip raises an error when
        fed an IP whose octets are strings'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.checkip,
            'a.b.c.d')

    def testCheckBadIpOversizedOctet(self):
        '''check to see that checkip raises an error when
        fed an IP which contains an octet of more than 255'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.checkip,
            '10.999.5.4')

    def testCheckGoodIp(self):
        '''check to see that checkip will return 1 for
        a valid IP address'''
        self.assertEqual(
            IpUtil.checkip(
                '192.168.9.5'),
            1)


    def testIp2IdBadId(self):
        '''check to see that ipasid will raise an error if
        passed the ID encoding of a bad IP'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.ipasid,
            'ip_10_999_9_8')


    def testIp2IdBadIp(self):
        '''check to see that ipasid will raise an error if
        passed the ID encoding of a bad IP'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.ipasid,
            '10.999.9.8')

    def testIp2IdGoodId(self):
        '''check to see that ipasid will succeed if passed
        a decent ID'''
        self.assertEqual(
            IpUtil.ipasid(
                'ip_192_168_9_8'),
            'ip_192_168_9_8')

    def testIp2IdGoodIp(self):
        '''check to see that ipasid will succeed if passed
        a decent IP'''
        self.assertEqual(
            IpUtil.ipasid(
                '192.168.9.8'),
            'ip_192_168_9_8')

    def testId2IpBadId(self):
        '''check to see that idasip will raise an error
        if passed an invalid ID'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.idasip,
            'ip_192_168_999_8')

    def testId2IpBadIp(self):
        '''check to see that idasip will raise an error
        if passed an invalid IP'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.idasip,
            '192.999.8.6')

    def testId2IpGoodId(self):
        '''check to see that idasip succeeds when
        passed a valid ID'''
        self.assertEqual(
            IpUtil.idasip(
                'ip_192_168_5_4'),
            '192.168.5.4')

    def testId2IpGoodIp(self):
        '''check to see that idasip succeeds when
        passed a valid IP'''
        self.assertEqual(
            IpUtil.idasip(
                '192.168.5.4'),
            '192.168.5.4')

    def testNumbIpBad(self):
        '''check to see that numbip won't try
        to convert an invalid ip'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.numbip,
            '999.129.0.9')

    def testNumbIpGood(self):
        '''check to see that numbip succeeds
        when given a valid IP'''
        self.assertEqual(
            IpUtil.numbip(
                '192.168.2.3'),
            3232236035)

    def testStripGood(self):
        '''check that the strip function can
        convert a number back into an IP'''
        self.assertEqual(
            IpUtil.strip(
                3232236035),
            '192.168.2.3')

    def testGetNetBadIp(self):
        '''check to make sure getnet fails
        for bad IPs'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.getnet,
            '999.2.4.1',
            '255.255.255.0')

    def testGetNetBadMask(self):
        '''check to make sure getnet fails
        for bad subnet masks'''
        self.assertRaises(
            IpUtil.IpAddressError,
            IpUtil.getnet,
            '192.168.2.3',
            '299.240.0.0')

    def testGetNetAllGood(self):
        '''check to make sure that getnet will
        succeed if it is passed a valid ip/subnet
        pair'''
        self.assertEqual(
            IpUtil.getnet(
                '192.168.2.3',
                '255.255.240.0'),
            3232235520)

    def testGetNetStr(self):
        '''check to make sure getnetstr works fine,
        which it should if the tests for strip and
        getnet passed'''
        self.assertEqual(
            IpUtil.getnetstr(
                '192.168.17.6',
                '255.255.240.0'),
            '192.168.16.0')

if __name__ == "__main__":
    unittest.main()
