#!/usr/bin/env python

import os
import unittest

import common

from Products.ZenUtils.path import zenPath


class Test_fixOpentsdbLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for Opentsdb is fixed as expected.
    """
    # Note that we are testing relative to 5.3.0 because 5.3.0 was the first
    # release to make logback.xml user-configurable for opentsdb.
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-fixOpentsdbLogFilters.json'
    migration_module_name = 'fixOpentsdbLogFilters'
    migration_class_name = 'FixOpentsdbLogFilters'

    expected_log_filters = dict()
    filterName = "hbasedaemon"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef

if __name__ == '__main__':
    unittest.main()
