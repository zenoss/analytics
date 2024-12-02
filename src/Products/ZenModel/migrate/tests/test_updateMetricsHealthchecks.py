# tests/test_updateMetricsHealthchecks.py

import os
import unittest

import common

class Test_UpdateMetricsHealthChecks(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'test_updateMetricsHealthchecks.json'
    expected_servicedef = 'test_updateMetricsHealthchecks_out.json'
    migration_module_name = 'updateMetricsHealthchecks'
    migration_class_name = 'UpdateMetricsHealthChecks'
