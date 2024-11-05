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
from Products.ZenUtils.path import zenPath

class test_addRabbitMQLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding LogFilters for RabbitMQ logs issue addressed by ZEN-28095
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3-updateRabbitMQLogPaths.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-addRabbitMQLogFilters.json' # Check against modified def
    migration_module_name = 'addRabbitMQLogFilters'
    migration_class_name = 'AddRabbitMQLogFilters'
    expected_log_filters = dict()

    filterName = "rabbitmq"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef
