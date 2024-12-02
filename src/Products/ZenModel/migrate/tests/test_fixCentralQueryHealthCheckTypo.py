#!/usr/bin/env python

import os
import unittest

import common


class Test_FixCentralQueryHealthCheckTypo(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that credentials are updated for centralquery and metricconsumer
    """
    initial_servicedef = 'zenoss-resmgr-lite-5.1.0.json'
    expected_servicedef = 'zenoss-resmgr-lite-5.1.0-fixCentralQueryHealthCheckTypo.json'
    migration_module_name = 'fixCentralQueryHealthCheckTypo'
    migration_class_name = 'FixCentralQueryHealthCheckTypo'


if __name__ == '__main__':
    unittest.main()
