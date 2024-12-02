import unittest
import common


class test_fixRabbitmqHealthCheck(
    unittest.TestCase, common.ServiceMigrationTestCase
):
    """Test rabbitmq endpoints for zauth and zenpython were updated.
    """

    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-fixRabbitmqHealthCheck.json'
    migration_module_name = 'fixRabbitmqHealthCheck'
    migration_class_name = 'FixRabbitmqHealthCheck'
