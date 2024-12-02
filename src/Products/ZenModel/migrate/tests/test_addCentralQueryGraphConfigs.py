#!/usr/bin/env python

import os
import unittest

import common


class Test_AddCentralQueryGraphConfigs(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that CentralQuery has a query rate graph added if it didn't already have one.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-addCentralQueryGraphConfigs.json'
    migration_module_name = 'addCentralQueryGraphConfigs'
    migration_class_name = 'AddCentralQueryGraphConfigs'
       

if __name__ == '__main__':
    unittest.main()

