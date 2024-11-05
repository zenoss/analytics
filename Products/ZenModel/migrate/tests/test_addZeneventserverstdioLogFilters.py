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

class test_addZeneventserverstdioLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding LogFilters for Zeneventserverstdio logs issue addressed by ZEN-28081
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updatedZeneventserverstdioLogFilter.json' # the filter spec was added

    migration_module_name = 'addZeneventserverstdioLogFilters'
    migration_class_name = 'AddZeneventserverstdioLogFilters'
    expected_log_filters = dict()

    filterName = "zeneventserver-stdio"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef
