#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateOpenTSDBSkipResolvedTags(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that open tsdb configs have the skip_unresolved_tagvs setting added/set.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-updateOpenTSDBSkipUnresolvedTags.json'
    migration_module_name = 'updateOpenTSDBSkipUnresolvedTags'
    migration_class_name = 'UpdateOpenTSDBSkipUnresolvedTags'

if __name__ == '__main__':
    unittest.main()

