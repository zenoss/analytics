#!/usr/bin/env python

import unittest
import common


class TestAllowGracefulShutdownForZEP(
    unittest.TestCase, common.ServiceMigrationTestCase,
):
    """Test whether the changes to the opentsdb-writer service were made.
    """
    initial_servicedef = 'zenoss-resmgr-6.5.0-init.json'
    expected_servicedef = 'zenoss-resmgr-6.5.0-allowGracefulShutdownForWriter.json'
    migration_module_name = 'allowGracefulShutdownForWriter'
    migration_class_name = 'AllowGracefulShutdownForWriter'


if __name__ == '__main__':
    unittest.main()
