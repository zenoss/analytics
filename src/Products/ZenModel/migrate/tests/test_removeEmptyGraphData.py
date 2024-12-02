#!/usr/bin/env python

import os
import unittest

import common


class Test_RemoveEmptyGraphData(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that RemoveEmptyGraphdata removes a few unused graphs.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-removeEmptyGraphdata.json'
    migration_module_name = 'removeEmptyGraphdata'
    migration_class_name = 'RemoveEmptyGraphData'
       

if __name__ == '__main__':
    unittest.main()

