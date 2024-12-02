#!/usr/bin/env python

import os
import unittest

import common


class Test_BeakerHTTPOnly(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that beaker is added to zope's config file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.2.json'
    expected_servicedef = 'zenoss-resmgr-5.1.2-beakerHttpOnly.json'
    migration_module_name = 'beakerHttpOnly'
    migration_class_name = 'BeakerHTTPOnly'


if __name__ == '__main__':
    unittest.main()

