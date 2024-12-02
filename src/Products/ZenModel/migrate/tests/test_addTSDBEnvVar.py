# tests/test_addTSDBEnvVar.py

import os
import unittest

import common


class Test_AddTsdbEnvVar (unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that environment variable is added to reader and writer service definitions
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-addTSDBEnvVar.json'
    migration_module_name = 'addTSDBEnvVar'
    migration_class_name = 'AddTSDBEnvVar'

