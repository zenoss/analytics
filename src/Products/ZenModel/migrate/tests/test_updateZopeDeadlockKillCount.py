import unittest
import common

class Test_updateZopeDeadlockKillCount(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test all 'deadlock_check' KillCounts were set to 5"
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0-updateZopeDeadlockInterval.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-updateZopeDeadlockKillCount.json'
    migration_module_name = 'updateZopeDeadlockKillCount'
    migration_class_name = 'UpdateZopeDeadlockKillCount'
