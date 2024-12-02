##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_checkHBaseTablesExist_resmgr(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating resmgr opentsdb reader service to check if HBase tables exist
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-checkHBaseTablesExist.json'
    migration_module_name = 'checkHBaseTablesExist'
    migration_class_name = 'CheckHBaseTablesExist'
