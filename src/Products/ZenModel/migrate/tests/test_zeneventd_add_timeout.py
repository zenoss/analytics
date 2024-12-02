import unittest

import common

class Test_DeleteRateOptionsForServices(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-zeneventd_add_timeout.json'
    migration_module_name = 'zeneventd_add_timeout'
    migration_class_name = 'ZeneventdAddTimeout'
