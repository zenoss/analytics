#!/usr/bin/env python

import os
import unittest

import common


class Test_AddAuditLogFlag(unittest.TestCase, common.ServiceMigrationTestCase):
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-audit-log.json'
    migration_module_name = 'addAuditLogFlag'
    migration_class_name = 'AddAuditLogFlag'


if __name__ == '__main__':
    unittest.main()
