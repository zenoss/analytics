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

class test_updateRabbitMQLogPaths(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the rabbitmq log path update succeeds.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updateRabbitMQLogPaths.json'
    migration_module_name = 'updateRabbitMQLogPaths'
    migration_class_name = 'UpdateRabbitMQLogPaths'
