#!/usr/bin/env python

import unittest

import common


class Test_updateDisableCorrelatorDefaultText(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0.json'
    expected_servicedef = \
        'zenoss-resmgr-6.1.0-updateDisableCorrelatorDefaultText.json'
    migration_module_name = 'updateDisableCorrelatorDefaultText'
    migration_class_name = 'UpdateDisableCorrelatorDefaultText'


if __name__ == '__main__':
    unittest.main()
