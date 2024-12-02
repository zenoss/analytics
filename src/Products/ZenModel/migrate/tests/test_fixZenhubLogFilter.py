#!/usr/bin/env python

import os
import unittest

import common


class Test_fixZenhubLogFilter(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for zenhub is fixed as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixZenhubLogFilter.json'
    migration_module_name = 'fixZenhubLogFilter'
    migration_class_name = 'FixZenhubLogFilter'


if __name__ == '__main__':
    unittest.main()
