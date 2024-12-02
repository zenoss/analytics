#!/usr/bin/env python

import unittest

import common


class Test_addQueueHighWaterMarkOption(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test queuehighwatermark configuration change for collector daemons.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-queuehighwatermark.json'
    migration_module_name = 'addQueueHighWaterMarkOption'
    migration_class_name = 'AddQueueHighWaterMarkOption'


if __name__ == '__main__':
    unittest.main()

