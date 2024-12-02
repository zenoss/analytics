#!/usr/bin/env python

import unittest

import common


class Test_AddADMZenHubWorkerService(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test the AddADMZenHubWorkerService class."""

    initial_servicedef = 'zenoss-resmgr-6.3.2.json'
    expected_servicedef = 'zenoss-resmgr-6.3.2-addADMZenHubWorkerService.json'
    migration_module_name = 'addADMZenHubWorkerService'
    migration_class_name = 'AddADMZenHubWorkerService'


if __name__ == '__main__':
    unittest.main()
