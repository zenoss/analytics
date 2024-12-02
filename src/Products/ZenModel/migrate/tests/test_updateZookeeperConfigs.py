#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateZookeeperConfigs(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that ZooKeeper configs were updated.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-updateZookeeperConfigs.json'
    migration_module_name = 'updateZookeeperConfigs'
    migration_class_name = 'UpdateZookeeperConfigs'


if __name__ == '__main__':
    unittest.main()

