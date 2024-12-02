import os
import unittest

import common


class Test_addOpenTSDBLogbackConfig (unittest.TestCase, common.ServiceMigrationTestCase):
    """
    Test that in OpenTSDB added logback.xml configuration file.
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5.json'
    expected_servicedef = 'zenoss-resmgr-5.1.5-addOpenTSDBLogbackConfig.json'
    migration_module_name = 'addOpenTSDBLogbackConfig'
    migration_class_name = 'addOpenTSDBLogbackConfig'
