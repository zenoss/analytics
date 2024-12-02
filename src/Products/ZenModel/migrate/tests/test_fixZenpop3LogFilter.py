#!/usr/bin/env python

import os
import unittest

import common


class Test_fixZenpop3LogFilter(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for zenpop3 is fixed as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixZenpop3LogFilter.json'
    migration_module_name = 'fixZenpop3LogFilter'
    migration_class_name = 'FixZenpop3LogFilter'


if __name__ == '__main__':
    unittest.main()
