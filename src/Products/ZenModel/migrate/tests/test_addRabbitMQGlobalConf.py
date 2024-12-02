#!/usr/bin/env python

import os
import unittest

import common


class Test_AddRabbitMQGlobalConf(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Tests that all services named RabbitMQ have an additional ConfigFile
    called global.conf.
    """
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-addrabbitmqglobalconf.json'
    migration_module_name = 'addRabbitMQGlobalConf'
    migration_class_name = 'AddRabbitMQGlobalConf'
       

if __name__ == '__main__':
    unittest.main()

