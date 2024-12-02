#!/usr/bin/env python


import unittest

import common


class TestUseRabbitmqScriptLauncher(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether services' start up commands are modified"""
    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-editServicesStartUp.json'
    migration_module_name = 'editServicesStartUp'
    migration_class_name = 'EditServicesStartUp'


if __name__ == '__main__':
    unittest.main() 

