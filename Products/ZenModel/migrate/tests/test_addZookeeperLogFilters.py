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

class test_addZookeeperLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding LogFilters for Zookeeper logs issue addressed by ZEN-28089
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addZookeeperLogFilters.json' # the filter spec was added

    migration_module_name = 'addZookeeperLogFilters'
    migration_class_name = 'AddZookeeperLogFilters'
    expected_log_filters = dict()

    filterName = "zookeeper"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef
