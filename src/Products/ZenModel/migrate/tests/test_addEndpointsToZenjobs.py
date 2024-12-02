#!/usr/bin/env python

import os
import unittest

import common


class Test_addEndpointsToZenjobs(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the addEndpointsToZenjobs migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-addEndpointsToZenjobs.json'
    migration_module_name = 'AddEndpointsToZenjobs'
    migration_class_name = 'AddEndpointsToZenjobs'
       

if __name__ == '__main__':
    unittest.main()
