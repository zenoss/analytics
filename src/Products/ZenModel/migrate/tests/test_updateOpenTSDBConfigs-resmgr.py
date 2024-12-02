#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateOpenTSDBConfigsResmgr(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that open tsdb config for reader and writer has had host set to 127.0.0.1.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-updateOpenTSDBConfigs.json'
    migration_module_name = 'updateOpenTSDBConfigs'
    migration_class_name = 'UpdateOpenTSDBConfigs'


if __name__ == '__main__':
    unittest.main()

