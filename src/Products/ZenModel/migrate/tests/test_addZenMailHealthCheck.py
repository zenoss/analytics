import unittest
import common

class Test_addZenmailHealthCheck(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the 'service_ready' healthcheck is added to zenmail"
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-zenmailHealthCheck.json'
    migration_module_name = 'addZenMailHealthCheck'
    migration_class_name = 'AddZenMailHealthCheck'
