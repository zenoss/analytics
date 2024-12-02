#!/usr/bin/env python

import os
import unittest

import common


class Test_convertRunsToCommands_core(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-core-5.0.5.json'
    expected_servicedef = 'zenoss-core-5.0.5-convertRunsToCommands.json'
    migration_module_name = 'convertRunsToCommands'
    migration_class_name = 'ConvertRunsToCommands'
       
class Test_convertRunsToCommands_resmgr(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.0.5.json'
    expected_servicedef = 'zenoss-resmgr-5.0.5-convertRunsToCommands.json'
    migration_module_name = 'convertRunsToCommands'
    migration_class_name = 'ConvertRunsToCommands'
       

if __name__ == '__main__':
    unittest.main()
