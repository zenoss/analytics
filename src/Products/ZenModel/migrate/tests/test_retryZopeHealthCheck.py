
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


class test_retryZopeHealthCheck(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that 'answering' healtheck is retrying on failure.
    """
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-retryZopeHealthCheck.json'
    migration_module_name = 'retryZopeHealthCheck'
    migration_class_name = 'RetryZopeHealthCheck'
