#!/usr/bin/env python

import os
import unittest

import common


class Test_addQuiltInstallCommand(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the addQuiltInstallCommand migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-addQuiltInstallCommand.json'
    migration_module_name = 'addQuiltInstallCommand'
    migration_class_name = 'AddQuiltInstallCommand'
       

if __name__ == '__main__':
    unittest.main()
