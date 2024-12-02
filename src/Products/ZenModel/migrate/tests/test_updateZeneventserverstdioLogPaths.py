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

class test_updateZeneventserverstdioLogPaths(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the zeneventserver-stdio log path update succeeds.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-updateZeneventserverstdioLogPaths.json'
    migration_module_name = 'updateZeneventserverstdioLogPaths'
    migration_class_name = 'UpdateZeneventserverstdioLogPaths'
