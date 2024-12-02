#!/usr/bin/env python

import os
import unittest

import common


class Test_templatizeCollectorEndpoints(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test the templatizeCollectorEndpoints migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-templatizeCollectorEndpoints.json'
    migration_module_name = 'templatizeCollectorEndpoints'
    migration_class_name = 'TemplatizeCollectorEndpoints'
       

if __name__ == '__main__':
    unittest.main()
