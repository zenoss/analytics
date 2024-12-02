#!/usr/bin/env python

import os
import unittest

import common


class Test_SetMariaDbTimeouts51x(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that MariaDB Timeout values are set to 7200 seconds
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-setMariaDbTimeouts51x.json'
    migration_module_name = 'setMariaDbTimeouts51x'
    migration_class_name = 'SetMariaDbTimeouts51x'


if __name__ == '__main__':
    unittest.main()
