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

class test_updateZodbConfigFiles(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating zodb config files to be dinamically generated from global.conf
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updateZodbConfigFiles.json'
    migration_module_name = 'updateZodbConfigFiles'
    migration_class_name = 'UpdateZodbConfigFiles'