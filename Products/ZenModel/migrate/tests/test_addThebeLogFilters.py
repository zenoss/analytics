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

class test_addThebeLogFilters(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test adding log filters for the Thebe release (ZEN-27982)
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = initial_servicedef        # because addThebeLogFilters doesn't change Service objects
    migration_module_name = 'addThebeLogFilters'
    migration_class_name = 'AddThebeLogFilters'
    expected_log_filters = dict()

    filterNames = ["pythondaemon", "supervisord", "z2_access_logs", "zappdaemon", "zeneventserver", "zope"]
    for filterName in filterNames:
        filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
        with open(zenPath(filename)) as filterFile:
            filterDef = filterFile.read()
            expected_log_filters[filterName] = filterDef
