#!/usr/bin/env python

import os
import unittest

import common


class Test_NoRabbitMQAddressAssignment(unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that the start and emergency shutdown levels are added to service definitions.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-noRabbitMQAddressAssignment.json'
    migration_module_name = 'noRabbitMQAddressAssignment'
    migration_class_name = 'noRabbitMQAddressAssignment'


if __name__ == '__main__':
    unittest.main()