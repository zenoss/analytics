#!/usr/bin/env python

import os
import unittest

import common


class Test_EnableNginxPagespeed(unittest.TestCase, common.ServiceMigrationTestCase):
    """  
    Test that 'pagespeed on' is in zproxy's config file. 
    """
    initial_servicedef = 'zenoss-resmgr-5.1.5-pagespeedoff.json' 
    expected_servicedef = 'zenoss-resmgr-5.1.5-enableNginxPagespeed.json' 
    migration_module_name = 'enableNginxPagespeed'
    migration_class_name = 'EnableNginxPagespeed'


if __name__ == '__main__':
    unittest.main()

