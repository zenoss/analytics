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

if __name__ == "__main__":
    execfile(os.path.join(sys.path[0], "framework.py"))

from Products.ZenRRD.parsers import uptime
from Products.ZenUtils.ZenDocTest import TestSuiteWithHooks, ZenDocTestRunner

DOCTEST_MODULES = [uptime]


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
