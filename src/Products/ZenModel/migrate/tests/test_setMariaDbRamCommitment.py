#!/usr/bin/env python

import os
import unittest

import common


class Test_SetMariaDbRamCommitment(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that MariaDB RAM Commitment value is changed from 2G to 4G
    """
    
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-setMariaDbModelRamCommitment.json'
    migration_module_name = 'setMariaDbConfigDefaults'
    migration_class_name = 'SetMariaDbConfigDefaults'

if __name__ == '__main__':
    unittest.main()

