# tests/test_EnableZproxyNginxPagespeed.py

import unittest

import common

class Test_EnableZproxyNginxPagespeed(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.1.5-pagespeed_off.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-enableZproxyNginxPagespeed.json'
    migration_module_name = 'EnableZproxyNginxPagespeed'
    migration_class_name = 'EnableZproxyNginxPagespeed'
