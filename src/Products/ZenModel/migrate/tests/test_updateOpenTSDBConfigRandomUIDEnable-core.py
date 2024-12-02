#!/usr/bin/env python

import unittest

import common


class Test_UpdateOpenTSDBConfigRandomUIDEnableCore(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that open tsdb config for reader and writer has had random UID parameter set to True.
    """
    initial_servicedef = 'zenoss-core-5.1.5.json'
    expected_servicedef = 'zenoss-core-5.1.5-updateOpenTsdbConfigRandomUidEnable.json'
    migration_module_name = 'updateOpenTSDBConfigRandomUIDEnable'
    migration_class_name = 'UpdateOpenTSDBConfigRandomUIDEnable'


if __name__ == '__main__':
    unittest.main()

