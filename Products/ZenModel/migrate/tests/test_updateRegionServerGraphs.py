#!/usr/bin/env python

import os
import unittest

import common

from Products.ZenUtils.path import zenPath


class Test_updateRegionServerGraphs(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the RegionServer opcount graphs are changed to rates.
    """
    initial_servicedef = 'zenoss-resmgr-5.2.3.json'
    expected_servicedef = 'zenoss-resmgr-5.2.3-updateRegionServerGraphs.json'
    migration_module_name = 'updateRegionServerGraphs'
    migration_class_name = 'UpdateRegionServerGraphs'

if __name__ == '__main__':
    unittest.main()
