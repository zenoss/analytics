#!/usr/bin/env python

import os
import unittest

import common


class Test_UseBeakerInZope(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that beaker is added to zope's config file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.2.json'
    expected_servicedef = 'zenoss-resmgr-5.1.2-defaultBeakerToSecure.json'
    migration_module_name = 'defaultBeakerToSecure'
    migration_class_name = 'DefaultBeakerToSecure'
       

if __name__ == '__main__':
    unittest.main()
