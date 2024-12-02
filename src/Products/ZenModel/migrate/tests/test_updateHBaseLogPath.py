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

class test_updateHbaseLogPath(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating HMaster and RegionServer log paths from /var/log/hbase to 
    /opt/hbase/logs
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updateHBaseLogPath.json'
    migration_module_name = 'updateHBaseLogPath'
    migration_class_name = 'UpdateHBaseLogPath'
