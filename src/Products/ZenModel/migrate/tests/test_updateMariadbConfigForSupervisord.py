#!/usr/bin/env python

import unittest
import common


class Test_updateMariadbConfigForSupervisord(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = \
        'zenoss-resmgr-6.5.0-updateMariadbConfigForSupervisord.json'
    migration_module_name = 'updateMariadbConfigForSupervisord'
    migration_class_name = 'UpdateMariadbConfigForSupervisord'


if __name__ == '__main__':
    unittest.main()
