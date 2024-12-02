#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateZeneventserverHealthCheck(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test that the healthcheck is updated."""

    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-updateZeneventserverHealthCheck.json'
    migration_module_name = 'updateZeneventserverHealthCheck'
    migration_class_name = 'UpdateZeneventserverHealthCheck'


if __name__ == '__main__':
    unittest.main()
