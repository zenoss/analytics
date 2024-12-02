##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from Testing import ZopeTestCase as ztc
from zope.component import testing


def test_suite():
    return unittest.TestSuite(
        [
            # Unit tests for your API
            # doctestunit.DocFileSuite(
            #    'README.txt', package='Products.ZenUI3.navigation',
            #    setUp=testing.setUp, tearDown=testing.tearDown),
            # doctestunit.DocTestSuite(
            #    module='Products.ZenUI3.mymodule',
            #    setUp=testing.setUp, tearDown=testing.tearDown),
            # Integration tests that use ZopeTestCase
            ztc.ZopeDocFileSuite(
                "README.txt",
                package="Products.ZenUI3.navigation",
                setUp=testing.setUp,
                tearDown=testing.tearDown,
            ),
            # ztc.FunctionalDocFileSuite(
            #    'browser.txt', package='Products.ZenUI3'),
        ]
    )


if __name__ == "__main__":
    unittest.main(defaultTest="test_suite")
