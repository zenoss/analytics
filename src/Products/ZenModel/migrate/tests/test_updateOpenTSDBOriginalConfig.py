##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_updateOpenTSDBOriginalConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating resmgr opentsdb/writer & reader with a new Original config.
    """
    initial_servicedef = 'zenoss-resmgr-5.0.5.json'
    expected_servicedef = 'zenoss-resmgr-5.0.5-updateOpenTSDBOriginalConfig.json'
    migration_module_name = 'updateOpenTSDBOriginalConfig'
    migration_class_name = 'updateOpenTSDBOriginalConfig'

if __name__ == '__main__':
    unittest.main()
