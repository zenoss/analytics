import unittest
import common

class Test_updateZopeDeadlockInterval(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test all 'deadlock_check' healthchecks Interval was increased from 30 to 60 sec"
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0-updateZopeDeadlockMaxtime.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-updateZopeDeadlockInterval.json'
    migration_module_name = 'updateZopeDeadlockInterval'
    migration_class_name = 'UpdateZopeDeadlockInterval'
