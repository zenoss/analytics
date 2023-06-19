#!/usr/bin/env python

import unittest
import common

from Products.ZenUtils.path import zenPath

class Test_addMariaDBLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for MariaDB is added as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.2.3.json'
    expected_servicedef = 'zenoss-resmgr-5.2.3-addMariaDBLogFilters.json'
    migration_module_name = 'addMariaDBLogFilters'
    migration_class_name = 'AddMariaDBLogFilters'

    expected_log_filters = dict()
    filterName = "mariadb"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef

if __name__ == '__main__':
    unittest.main()
