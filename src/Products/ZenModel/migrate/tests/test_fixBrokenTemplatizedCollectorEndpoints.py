#!/usr/bin/env python

import os
import unittest

import common


class Test_fixBrokenTemplatizedCollectorEndpoints(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test that the templatizeCollectorEndpoints migration will fix mangled endpoints created by a previous version of this migration."""

    # class variables controlling common.ServiceMigrationTestCase 
    initial_servicedef = 'zenoss-resmgr-5.0.6_1-brokenTemplatizedCollectorEndpoints.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-templatizeCollectorEndpoints.json'
    migration_module_name = 'templatizeCollectorEndpoints'
    migration_class_name = 'TemplatizeCollectorEndpoints'
       

if __name__ == '__main__':
    unittest.main()
