#!/usr/bin/env python

import os
import unittest

import common


class Test_SetZeneventMaxInstances(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that we set the max instances to 1 when the setting didn't exist.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-setZeneventMaxInstances.json'
    migration_module_name = 'setZeneventMaxInstances'
    migration_class_name = 'SetZeneventMaxInstances'


if __name__ == '__main__':
    unittest.main()

