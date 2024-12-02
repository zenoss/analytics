#!/usr/bin/env python

import unittest
import common

class TestAddTagToImage(unittest.TestCase, common.ServiceMigrationTestCase):

    initial_servicedef = 'test_addTagToImage.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    migration_module_name = 'addTagToImages'
    migration_class_name = 'AddTagToImages'
