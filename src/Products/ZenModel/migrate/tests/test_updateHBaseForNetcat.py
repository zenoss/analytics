#!/usr/bin/env python

import os
import unittest

import common


class Test_UpdateHBaseForNetcat(unittest.TestCase, common.ServiceMigrationTestCase):
    """Test that all the netcat commands have been updates"""

    initial_servicedef = 'zenoss-resmgr-5.0.6_1.json'
    expected_servicedef = 'zenoss-resmgr-5.0.6_1-updateHBaseForNetcat.json'
    migration_module_name = 'updateHBaseForNetcat'
    migration_class_name = 'UpdateHBaseForNetcat'


if __name__ == '__main__':
    unittest.main()
