# tests/test_changeDefaultZauthZserverThreads.py

import unittest

import common

class Test_ChangeDefaultZauthZserverThreads(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-changeDefaultZauthZserverThreads.json'
    migration_module_name = 'ChangeDefaultZauthZserverThreads'
    migration_class_name = 'ChangeDefaultZauthZserverThreads'
