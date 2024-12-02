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


class test_FixDatapointsFormat(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the zenpop3 and zenmail have correct datapoints format.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-FixDatapointsFormat.json'
    migration_module_name = 'FixDatapointsFormat'
    migration_class_name = 'FixDatapointsFormat'

