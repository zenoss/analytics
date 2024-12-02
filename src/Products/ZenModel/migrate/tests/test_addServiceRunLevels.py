#!/usr/bin/env python

import os
import unittest

import common


class Test_AddServiceRunLevels(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the start and emergency shutdown levels are added to service definitions.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addServiceRunLevels.json'
    migration_module_name = 'addServiceRunLevels'
    migration_class_name = 'AddServiceRunLevels'


if __name__ == '__main__':
    unittest.main()
