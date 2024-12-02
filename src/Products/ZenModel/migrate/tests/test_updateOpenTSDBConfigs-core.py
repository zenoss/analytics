#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateOpenTSDBConfigsCore(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that open tsdb config for reader and writer has had host set to 127.0.0.1.
    """
    initial_servicedef = 'zenoss-core-5.0.6_193.json'
    expected_servicedef = 'zenoss-core-5.0.6_193-updateOpenTSDBConfigs.json'
    migration_module_name = 'updateOpenTSDBConfigs'
    migration_class_name = 'UpdateOpenTSDBConfigs'


if __name__ == '__main__':
    unittest.main()

