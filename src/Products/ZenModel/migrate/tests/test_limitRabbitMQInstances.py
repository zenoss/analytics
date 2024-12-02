import unittest

import common

class Test_LimitRabbitMQInstances(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'test_limitRabbitMQInstances_in.json'
    expected_servicedef = 'test_limitRabbitMQInstances_out.json'
    migration_module_name = 'limitRabbitMQInstances'
    migration_class_name = 'LimitRabbitMQInstances'
