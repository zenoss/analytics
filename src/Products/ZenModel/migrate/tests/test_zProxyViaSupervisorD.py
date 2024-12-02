#!/usr/bin/env python

import os
import unittest

import common


class test_ZProxyViaSupervisorD(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-ZProxyViaSupervisorD.json'
    migration_module_name = 'zProxyViaSupervisorD'
    migration_class_name = 'ZProxyViaSupervisorD'


if __name__ == '__main__':
    unittest.main()
