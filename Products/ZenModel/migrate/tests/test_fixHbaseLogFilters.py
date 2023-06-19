#!/usr/bin/env python

import os
import unittest

import common

from Products.ZenUtils.path import zenPath


class Test_fixHbaseLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for Hbase is fixed as expected.
    """
    # Note that we are testing relative to 5.2.x because 5.2.0 was the first
    # release to source log files out of /opt/hbase/logs/
    initial_servicedef = 'zenoss-resmgr-5.2.3.json'
    expected_servicedef = 'zenoss-resmgr-5.2.3-fixHbaseLogFilters.json'
    migration_module_name = 'fixHbaseLogFilters'
    migration_class_name = 'FixHbaseLogFilters'

    expected_log_filters = dict()
    filterName = "hbasedaemon"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef

if __name__ == '__main__':
    unittest.main()
