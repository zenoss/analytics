# tests/test_EnableZproxyNginxPagespeed.py

import unittest

import common

class Test_EnableZproxyNginxPagespeedOrigConfig(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.1.5-pagespeedoff.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-enableZproxyNginxPagespeedOrigConfig.json'
    migration_module_name = 'EnableZproxyNginxPagespeedOrigConfig'
    migration_class_name = 'EnableZproxyNginxPagespeedOrigConfig'
