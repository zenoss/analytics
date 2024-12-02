#!/usr/bin/env python

import os
import unittest

import common


class Test_MakeMemcachedUpdates(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that memcache's answering script is updated,
    and a memcache config is added.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-makeMemcachedUpdates.json'
    migration_module_name = 'makeMemcachedUpdates'
    migration_class_name = 'MakeMemcachedUpdates'
       

if __name__ == '__main__':
    unittest.main()
