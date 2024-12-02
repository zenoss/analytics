import unittest

import common

class Test_AddZenossPublicEndpoint(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'test_addZenossPublicEndpoint_in.json'
    expected_servicedef = 'test_addZenossPublicEndpoint_out.json'
    migration_module_name = 'addZenossPublicEndpoint'
    migration_class_name = 'AddZenossPublicEndpoint'
