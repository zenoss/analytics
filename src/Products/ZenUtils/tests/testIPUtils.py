##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import unittest
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.IpUtil import ensureIp


class IpUtilsTest(BaseTestCase):
    """ Tests functions on the IpUtils module"""
    
    def testEnsureIp(self):
        ip = '10'
        self.assertEqual(ensureIp(ip), '10.0.0.0')

        # strips the characters
        ip = '10a.12.aaa'
        self.assertEqual(ensureIp(ip), '10.12.0.0')

        # invalid number
        ip = '1212121212121'
        self.assertEqual(ensureIp(ip), '0.0.0.0')
                         
def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(IpUtilsTest),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
