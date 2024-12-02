#!/usr/bin/env python

import os
import unittest

import common


class Test_fixZenmailLogFilter(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for zenmail is fixed as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixZenmailLogFilter.json'
    migration_module_name = 'fixZenmailLogFilter'
    migration_class_name = 'FixZenmailLogFilter'


if __name__ == '__main__':
    unittest.main()
