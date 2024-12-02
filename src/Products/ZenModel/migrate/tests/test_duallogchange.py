#!/usr/bin/env python

import os
import unittest

import common


class Test_DuallogChange(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that service Starup values use --logfileonly instead of --duallog
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-duallogchange.json'
    migration_module_name = 'duallogchange'
    migration_class_name = 'DualLogChange'
       

if __name__ == '__main__':
    unittest.main()
