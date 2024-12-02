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

class test_fixMariadbHealthCheck(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the Zauth has a new healcheck.
    """
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-fixMariadbHealthCheck.json'
    migration_module_name = 'fixMariadbHealthCheck'
    migration_class_name = 'FixMariadbHealthCheck'
