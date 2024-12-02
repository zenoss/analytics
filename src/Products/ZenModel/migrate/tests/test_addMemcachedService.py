#!/usr/bin/env python

import os
import unittest

import common


class Test_AddMemcachedService(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that a new memcached service is created.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1-nomemcached.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-addMemcachedService.json'
    migration_module_name = 'addMemcachedService'
    migration_class_name = 'AddMemcachedService'
       

if __name__ == '__main__':
    unittest.main()
