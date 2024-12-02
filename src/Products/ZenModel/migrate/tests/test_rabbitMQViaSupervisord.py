#!/usr/bin/env python

import os
import unittest

import common


class Test_RunRabbitMQViaSupervisord(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that rabbitmq configs have new supervisord config files and updated startup commands.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-rabbitMQViaSupervisord.json'
    migration_module_name = 'rabbitMQViaSupervisord'
    migration_class_name = 'RunRabbitMQViaSupervisord'

if __name__ == '__main__':
    unittest.main()

