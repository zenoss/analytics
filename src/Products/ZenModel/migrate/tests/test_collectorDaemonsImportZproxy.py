import unittest

import common

class test_collectorDaemonsImportZproxy(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test zproxy was added as an imported endpoint to all collector services
    """

    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-testCollectorDaemonsImportZproxy.json'
    migration_module_name = 'collectorDaemonsImportZproxy'
    migration_class_name = 'CollectorDaemonsImportZproxy'
