##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from types import ModuleType

from Products.ZenUtils.ZenDocTest import ZenDocTestRunner
from Products.ZenUtils.ZenDocTest import TestSuiteWithHooks

from Products import ZenEvents as TARGET_MODULE

def get_submodules(mod):
    vals = mod.__dict__.values()
    allmods = filter(lambda x:type(x)==ModuleType, vals)
    submods = filter(lambda x:x.__name__.startswith(mod.__name__), allmods)
    return submods

def test_suite():
    suite = TestSuiteWithHooks()
    zdtr = ZenDocTestRunner()
    suite.setUp, suite.tearDown = zdtr.setUp, zdtr.tearDown
    zdtr.add_modules(get_submodules(TARGET_MODULE))
    for dtsuite in zdtr.get_suites():
        suite.addTest(dtsuite)
    return suite

if __name__=="__main__":
    if None: framework = None
    framework()
