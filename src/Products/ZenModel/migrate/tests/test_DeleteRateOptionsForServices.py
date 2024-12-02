import unittest

import common

class Test_DeleteRateOptionsForServices(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-deleteRateOptions.json'
    migration_module_name = 'deleteRateOptionsForServices'
    migration_class_name = 'DeleteRateOptionsForServices'

