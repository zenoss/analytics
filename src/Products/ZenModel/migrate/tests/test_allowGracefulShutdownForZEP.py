#!/usr/bin/env python

import unittest
import common


class TestAllowGracefulShutdownForZEP(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether the changes to the zeneventserver service were made.
    """
    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-allowGracefulShutdownForZEP.json'
    migration_module_name = 'allowGracefulShutdownForZEP'
    migration_class_name = 'AllowGracefulShutdownForZEP'


if __name__ == '__main__':
    unittest.main()
