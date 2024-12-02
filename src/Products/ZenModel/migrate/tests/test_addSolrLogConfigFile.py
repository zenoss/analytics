##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import common
import unittest

class test_addSolrLogConfigFile(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that audit log levev log is added.
    """
    initial_servicedef = 'zenoss-resmgr-6.1.0.json'
    expected_servicedef = 'zenoss-resmgr-6.1.0-addSolrLogConfigFile.json'
    migration_module_name = 'addSolrLogConfigFile'
    migration_class_name = 'addSolrLogConfigFile'


if __name__ == '__main__':
    unittest.main()
