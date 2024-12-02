#!/usr/bin/env python

import unittest

import common


class Test_addWriterEndpointToCQ(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the addWriterEndpointToCQ migration."""

    # class variables controlling common.ServiceMigrationTestCase
    initial_servicedef = 'zenoss-resmgr-5.3.0.json'
    expected_servicedef = 'zenoss-resmgr-5.3.0-addWriterEndpointToCQ.json'
    migration_module_name = 'addWriterEndpointToCQ'
    migration_class_name = 'AddWriterEndpointToCQ'


if __name__ == '__main__':
    unittest.main()

