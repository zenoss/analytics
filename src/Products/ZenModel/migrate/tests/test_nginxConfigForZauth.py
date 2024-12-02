#!/usr/bin/env python

import os
import unittest

import common


class Test_nginxConfigForZauth(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test nginx configuration change for zauth.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-nginxConfigForZauth.json'
    migration_module_name = 'nginxConfigForZauth'
    migration_class_name = 'NginxConfigForZauth'


if __name__ == '__main__':
    unittest.main()
