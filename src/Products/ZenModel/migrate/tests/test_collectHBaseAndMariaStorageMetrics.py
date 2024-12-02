#!/usr/bin/env python

import unittest

import common


class Test_collectHBaseAndMariaStorageMetrics(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test collectHBaseAndMariaStorageMetrics migration.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-collectHBaseAndMariaStorageMetrics.json'
    migration_module_name = 'collectHBaseAndMariaStorageMetrics'
    migration_class_name = 'CollectHBaseAndMariaStorageMetrics'


if __name__ == '__main__':
    unittest.main()
