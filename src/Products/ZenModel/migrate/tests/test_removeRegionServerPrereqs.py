#!/usr/bin/env python

import os
import unittest

import common


class Test_RemoveRegionServerPrereqs(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that all prereqs are removed from RegionServer service definition.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-removeRegionServerPrereqs.json'
    migration_module_name = 'removeRegionServerPrereqs'
    migration_class_name = 'RemoveRegionServerPrereqs'


if __name__ == '__main__':
    unittest.main()
