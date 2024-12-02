#!/usr/bin/env python

import common
import unittest

class Test_MariaDBPoolAllocations(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the Maria DB pool allocation default value replacement
    """
    initial_servicedef = 'zenoss-core-5.0.5.json'
    expected_servicedef = 'zenoss-core-5.0.5-updateMariaDBPoolAlloc.json'
    migration_module_name = 'updateMariaDbPoolAllocations'
    migration_class_name = 'UpdateMariaDBPoolAlloc'


if __name__ == '__main__':
    unittest.main()
