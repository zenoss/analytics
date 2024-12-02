#!/usr/bin/env python

import os
import unittest

import common


class Test_ReplicateCollectorRedis(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that all prereqs are removed from RegionServer service definition.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-replicateCollectorRedis.json'
    migration_module_name = 'replicateCollectorRedis'
    migration_class_name = 'ReplicateCollectorRedis'


if __name__ == '__main__':
    unittest.main()
