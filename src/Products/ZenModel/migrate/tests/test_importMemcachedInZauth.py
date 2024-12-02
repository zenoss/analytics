import unittest

import common

class test_importMemcachedInZauth(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test memcached was added as an imported endpoint to zauth.
    """

    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-importMemcachedInZauth.json'
    migration_module_name = 'importMemcachedInZauth'
    migration_class_name = 'ImportMemcachedInZauth'

