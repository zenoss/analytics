#!/usr/bin/env python

import unittest

import common


class Test_addZepEndpointToZeneventd(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the addZepEndpointToZeneventd migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-addZepEndpointToZeneventd.json'
    migration_module_name = 'AddZepEndpointToZeneventd'
    migration_class_name = 'AddZepEndpointToZeneventd'


if __name__ == '__main__':
    unittest.main()

