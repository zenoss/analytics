#!/usr/bin/env python

import unittest
import common


class TestUseRabbitmqScriptLauncher(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether the new rabbitmq.sh script is installed.
    """
    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-useRabbitmqScriptLauncher.json'
    migration_module_name = 'useRabbitmqScriptLauncher'
    migration_class_name = 'UseRabbitmqScriptLauncher'


if __name__ == '__main__':
    unittest.main()
