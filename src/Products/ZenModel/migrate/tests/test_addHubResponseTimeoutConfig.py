#!/usr/bin/env python

import unittest

import common


class Test_addHubResponseTimeoutConfig(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the AddHubResponseTimeoutConfig class."""

    initial_servicedef = 'zenoss-resmgr-6.3.2.json'
    expected_servicedef = 'zenoss-resmgr-6.3.2-addHubResponseTimeoutConfig.json'
    migration_module_name = 'addHubResponseTimeoutConfig'
    migration_class_name = 'AddHubResponseTimeoutConfig'


if __name__ == '__main__':
    unittest.main()
