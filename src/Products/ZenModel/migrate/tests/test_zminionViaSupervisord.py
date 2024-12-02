#!/usr/bin/env python

import os
import unittest

import common


class Test_RunZminionViaSupervisord(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that each individual migration making use of servicemigration does
    as it promises.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-zminionViaSupervisord.json'
    migration_module_name = 'zminionViaSupervisord'
    migration_class_name = 'RunZminionViaSupervisord'
       

if __name__ == '__main__':
    unittest.main()
