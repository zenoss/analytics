#!/usr/bin/env python

import os
import unittest

import common


class Test_addHCUserAgents(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that all healthchecks that use curl have a user-agent string.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addHCUserAgents.json'
    migration_module_name = 'addHCUserAgents'
    migration_class_name = 'AddHCUserAgents'


if __name__ == '__main__':
    unittest.main()

