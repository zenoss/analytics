#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateRedisBindAddress(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating the redis bind address setting
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-updateRedisBindAddress.json'
    migration_module_name = 'UpdateRedisBindAddress'
    migration_class_name = 'UpdateRedisBindAddress'

if __name__ == '__main__':
    unittest.main()

