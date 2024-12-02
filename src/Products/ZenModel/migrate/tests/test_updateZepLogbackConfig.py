import os
import unittest
import common


class Test_UpdateZepLogbackConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test that the logback.xml file is updated."""

    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-updateZepLogbackConfig.json'
    migration_module_name = 'updateZepLogbackConfig'
    migration_class_name = 'UpdateZepLogbackConfig'


if __name__ == '__main__':
    unittest.main()
