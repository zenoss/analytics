import unittest
import common

class Test_updateZopeDeadlockMaxtime(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the 'deadlock_check' healthcheck is added to all zopes"
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0-addZopeDeadlockHC.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-updateZopeDeadlockMaxtime.json'
    migration_module_name = 'updateZopeDeadlockMaxtime'
    migration_class_name = 'UpdateZopeDeadlockMaxtime'
