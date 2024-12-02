#!/usr/bin/env python

import unittest

import common


class Test_separateZenHubWorkers(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-setPreferSeparateHostPolicy.json'
    migration_module_name = 'setPreferSeparateHostPolicy'
    migration_class_name = 'SetPreferSeparateHostPolicy'


if __name__ == '__main__':
    unittest.main()
