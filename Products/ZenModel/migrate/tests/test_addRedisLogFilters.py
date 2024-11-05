#!/usr/bin/env python

import os
import unittest

import common

from Products.ZenUtils.path import zenPath


class Test_addRedisLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the log filter for Redis is added as expected.
    """
    initial_servicedef = 'zenoss-resmgr-5.2.3.json'
    expected_servicedef = 'zenoss-resmgr-5.2.3-addRedisLogFilters.json'
    migration_module_name = 'addRedisLogFilters'
    migration_class_name = 'AddRedisLogFilters'

    expected_log_filters = dict()
    filterName = "redis"
    filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
    with open(zenPath(filename)) as filterFile:
        filterDef = filterFile.read()
        expected_log_filters[filterName] = filterDef

if __name__ == '__main__':
    unittest.main()
