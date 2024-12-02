#!/usr/bin/env python

import unittest

import common


class Test_updateRateOptionsForMetricShipper(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updateRateOptionsForMetricShipper migration.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-updateRateOptionsForMetricShipper.json'
    migration_module_name = 'updateRateOptionsForMetricShipper'
    migration_class_name = 'UpdateRateOptionsForMetricShipper'


if __name__ == '__main__':
    unittest.main()
