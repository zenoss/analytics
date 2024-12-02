#!/usr/bin/env python

import os
import unittest

import common


class Test_SetMariaDbBufferPoolSize(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that MariaDB Timeout values are set to 7200 seconds
    """
    initial_servicedef = 'zenoss-core-5.0.6_193.json'
    expected_servicedef = 'zenoss-core-5.0.6_193-setMariaDbBufferPoolSize.json'
    migration_module_name = 'setMariaDbConfigDefaults'
    migration_class_name = 'SetMariaDbConfigDefaults'

if __name__ == '__main__':
    unittest.main()

