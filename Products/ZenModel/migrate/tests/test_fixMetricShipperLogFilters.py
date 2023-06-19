#!/usr/bin/env python

import os
import unittest

import common

from Products.ZenUtils.path import zenPath


class Test_fixMetricShipperLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for MetricShipper is fixed as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-fixMetricShipperLogFilters.json'
    migration_module_name = 'fixMetricShipperLogFilters'
    migration_class_name = 'FixMetricShipperLogFilters'

    expected_log_filters = dict()
    filterName = "glog"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef

if __name__ == '__main__':
    unittest.main()
