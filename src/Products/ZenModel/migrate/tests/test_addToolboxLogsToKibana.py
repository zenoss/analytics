#!/usr/bin/env python

import os
import unittest

import common


class Test_addToolboxLogsToKibana(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test to make sure that logs added correctly.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addToolboxLogsToKibana.json'
    migration_module_name = 'addToolboxLogsToKibana'
    migration_class_name = 'AddToolboxLogsToKibana'


if __name__ == '__main__':
    unittest.main()
    