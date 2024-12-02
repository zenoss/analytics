#!/usr/bin/env python

import os
import unittest

import common


class Test_RunEnableCommitOnUpgrade(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that each individual migration making use of servicemigration does
    as it promises.
    """
    # Note that the usual order of the service defs is reversed: we start from 
    #  the non-default version and migrate to the default, because the default 
    #  has the desired change already.
    initial_servicedef = 'zenoss-resmgr-5.0.6_1-enableCommitOnUpgrade.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    migration_module_name = 'enableCommitonUpgrade'
    migration_class_name = 'EnableCommitOnUpgrade'
       

if __name__ == '__main__':
    unittest.main()
