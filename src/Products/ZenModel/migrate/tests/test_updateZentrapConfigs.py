import unittest

import common


class test_UpdateZentrapConfigs(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Tests that a "zentrap.filter.conf" is added as a config file to all zentrap services; updates zentrap.conf to latest
    """
    initial_servicedef = "zenoss-resmgr-5.0.6_1.json"
    expected_servicedef = "zenoss-resmgr-5.0.6_1-updateZentrapConfigs.json"
    migration_module_name = 'updateZentrapConfigs'
    migration_class_name = "UpdateZentrapConfigs"
