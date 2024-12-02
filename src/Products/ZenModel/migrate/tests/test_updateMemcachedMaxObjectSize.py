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

class test_updateMemcachedMaxObjectSize(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test updating memcached config file to pass zodb-cache-max-object-size
    """
    initial_servicedef = 'zenoss-resmgr-5.1.3.json'
    expected_servicedef = 'zenoss-resmgr-5.1.3-updateMemcachedMaxObjectSize.json'
    migration_module_name = 'updateMemcachedMaxObjectSize'
    migration_class_name = 'UpdateMemcachedMaxObjectSize'