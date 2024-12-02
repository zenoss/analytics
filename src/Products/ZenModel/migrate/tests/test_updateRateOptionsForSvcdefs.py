import unittest

import common

class Test_UpdateRateOptionsForSvcdefs(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'test_updateRateOptionsForSvcdefs_in.json'
    expected_servicedef = 'test_updateRateOptionsForSvcdefs_out.json'
    migration_module_name = 'updateRateOptionsForSvcdefs'
    migration_class_name = 'UpdateRateOptionsForSvcdefs'
