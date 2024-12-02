#!/usr/bin/env python

import os
import unittest

import common


class Test_addDebugZopesSvcDef(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that missedRuns threshold is added to collector services.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addDebugZopesSvcDef.json'
    migration_module_name = 'addDebugZopesSvcDef'
    migration_class_name = 'AddDebugZopesSvcDef'


if __name__ == '__main__':
    unittest.main()
