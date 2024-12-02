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

class test_updateOpenTsdbCreateTables_resmgr(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating resmgr opentsdb/writer service to initialize opentsdb for instance 0
    """
    # Note that even though the change was in the 5.1.2 service definition, it 
    # not in the corresponding testing json file.   We'll use that one.
    initial_servicedef = 'zenoss-resmgr-5.1.2.json'
    expected_servicedef = 'zenoss-resmgr-5.1.2-updateOpenTsdbCreateTables.json'
    migration_module_name = 'updateOpenTsdbCreateTables'
    migration_class_name = 'UpdateOpenTsdbCreateTables'

class test_updateOpenTsdbCreateTables_core(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating core opentsdb service to initialize opentsdb only for instance 0
    """
    initial_servicedef = 'zenoss-core-5.1.1.json'
    expected_servicedef = 'zenoss-core-5.1.1-updateOpenTsdbCreateTables.json'
    migration_module_name = 'updateOpenTsdbCreateTables'
    migration_class_name = 'UpdateOpenTsdbCreateTables'
