##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
import common


class test_addOpentsdbHbaseConnectionHealthCheck(
    unittest.TestCase, common.ServiceMigrationTestCase
):
    """Test Opentsdb reader and writer healthchecks for Hbase
    connectivity were added successfully
    """

    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-addOpentsdbHbaseConnectionHealthCheck.json'
    migration_module_name = 'addOpentsdbHbaseConnectionHealthCheck'
    migration_class_name = 'AddOpentsdbHbaseConnectionHealthCheck'


class test_addOpentsdbHbaseConnectionHealthCheck_resmgr_lite(
    unittest.TestCase, common.ServiceMigrationTestCase
):
    """Test Opentsdb reader and writer healthchecks for Hbase
    connectivity were added successfully
    """

    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-addOpentsdbHbaseConnectionHealthCheck.json'
    migration_module_name = 'addOpentsdbHbaseConnectionHealthCheck'
    migration_class_name = 'AddOpentsdbHbaseConnectionHealthCheck'
