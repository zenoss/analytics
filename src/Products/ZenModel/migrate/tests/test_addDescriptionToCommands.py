#!/usr/bin/env python

import os
import unittest

import common


class Test_addDescriptionToCommands(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test that a Description field is added to most Command objects."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.1.2.json'
    expected_servicedef = 'zenoss-resmgr-5.1.2-addDescriptionToCommands.json'
    migration_module_name = 'addDescriptionToCommands'
    migration_class_name = 'AddDescriptionToCommands'
       

if __name__ == '__main__':
    unittest.main()
