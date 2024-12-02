# tests/test_removeUCSPMVhostEndpoint.py

import unittest

import common

class test_removeUCSPMVhostEndpoint(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-ucspm-5.1.11.json'
    expected_servicedef = 'zenoss-ucspm-5.1.11-removeUCSPMVhostEndpoint.json'
    migration_module_name = 'removeUCSPMVhostEndpoint'
    migration_class_name = 'removeUCSPMVhostEndpoint'

if __name__ == '__main__':
    unittest.main()
