#!/usr/bin/env python

import unittest

import common


class Test_increaseZauthDefaultInstanceCount(
        unittest.TestCase, common.ServiceMigrationTestCase):
    """
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0.json'
    expected_servicedef = \
        'zenoss-resmgr-6.1.0-increaseZauthDefaultInstanceCount.json'
    migration_module_name = 'increaseZauthDefaultInstanceCount'
    migration_class_name = 'IncreaseZauthDefaultInstanceCount'


if __name__ == '__main__':
    unittest.main()
