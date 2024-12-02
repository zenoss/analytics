#!/usr/bin/env python

import os
import unittest

import common


class Test_updateZopeAnsweringHealthChecks(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the UpdateZProxyHealthCheck migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.1.2.json'
    expected_servicedef = 'zenoss-resmgr-5.1.2_1-updateZopeAnsweringHealthChecks.json'
    migration_module_name = 'updateZopeAnsweringHealthChecks'
    migration_class_name = 'UpdateZopeAnsweringHealthChecks'
       

if __name__ == '__main__':
    unittest.main()
