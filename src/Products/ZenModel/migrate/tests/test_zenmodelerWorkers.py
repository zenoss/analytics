import unittest
import common

class Test_zenmodelerWorkers(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that worker options to are added to zenmodeler"
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-zenmodelerWorkers.json'
    migration_module_name = 'zenmodelerWorkers'
    migration_class_name = 'zenmodelerWorkers'
