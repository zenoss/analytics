##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest


class test_increaseMemcachedMemory(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating memcached ramCommitment
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-increaseMemcachedMemory.json'
    migration_module_name = 'increaseMemcachedMemory'
    migration_class_name = 'IncreaseMemcachedMemory'

if __name__ == '__main__':
    unittest.main()
