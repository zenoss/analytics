#!/usr/bin/env python

import os
import unittest

import common


class test_UpdateNginxKibanaRule(unittest.TestCase, common.ServiceMigrationTestCase):
    #this one has the old kibana rule in it
    initial_servicedef = 'zenoss-ucspm-5.1.11.json'
    expected_servicedef = 'zenoss-ucspm-5.1.11-updateNginxKibanaRule.json'
    migration_module_name = 'updateNginxKibanaRule'
    migration_class_name = 'UpdateNginxKibanaRule'


if __name__ == '__main__':
    unittest.main()

