#!/usr/bin/env python

import os
import unittest

import common


class Test_fixZopeHealthCheck(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the FixZopeHealthCheck migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-core-5.0.6_193.json'
    expected_servicedef = 'zenoss-core-5.0.6_193-fixZopeHealthCheck.json'
    migration_module_name = 'fixZopeHealthCheck'
    migration_class_name = 'FixZopeHealthCheck'
       

if __name__ == '__main__':
    unittest.main()
