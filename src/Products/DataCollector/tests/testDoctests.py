##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import sys

from Products.ZenUtils.ZenDocTest import TestSuiteWithHooks, ZenDocTestRunner

from Products.DataCollector import CommandPluginUtils

if __name__ == "__main__":
    execfile(os.path.join(sys.path[0], "framework.py"))

DOCTEST_MODULES = [CommandPluginUtils]


def test_suite():
    suite = TestSuiteWithHooks()
    zdtr = ZenDocTestRunner()
    suite.setUp, suite.tearDown = zdtr.setUp, zdtr.tearDown
    zdtr.add_modules(DOCTEST_MODULES)
    for dtsuite in zdtr.get_suites():
        suite.addTest(dtsuite)
    return suite


if __name__ == "__main__":
    if None:
        framework = None
    framework()
