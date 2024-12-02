#!/usr/bin/env python

import os
import unittest

import common


class Test_fixZenactiondLogFilter(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for zenactiond is fixed as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixZenactiondLogFilter.json'
    migration_module_name = 'fixZenactiondLogFilter'
    migration_class_name = 'FixZenactiondLogFilter'


if __name__ == '__main__':
    unittest.main()
