#!/usr/bin/env python

import unittest

import common


class Test_MarkHubServices(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test the MarkHubServices class."""

    initial_servicedef = 'zenoss-resmgr-6.5.0.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-markHubServices.json'
    migration_module_name = 'markHubServices'
    migration_class_name = 'MarkHubServices'


if __name__ == '__main__':
    unittest.main()
