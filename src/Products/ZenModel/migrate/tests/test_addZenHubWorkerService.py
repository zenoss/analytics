#!/usr/bin/env python

import unittest

import common


class Test_separateZenHubWorkers(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-addZenHubWorkerService.json'
    migration_module_name = 'addZenHubWorkerService'
    migration_class_name = 'AddZenHubWorkerService'


if __name__ == '__main__':
    unittest.main()
