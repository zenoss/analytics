##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os.path

from Products.DataCollector.Plugins import PluginLoader, CoreImporter
from Products.ZenTestCase.BaseTestCase import BaseTestCase


def _here(*x):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)


TEST_PACKAGE = _here("plugins")


class ImportPlugins(BaseTestCase):
    def test_simple(self):
        """
        A trivial collector plugin.
        """
        loader = PluginLoader(
            _here("plugins"), "zenoss.noimports", "plugins", CoreImporter()
        )
        # We just care that it doesn't raise anything
        plugin = loader.create()
        self.assertEqual(plugin.MARKER, "abcdefg")

    def test_internal_imports(self):
        """
        Collector plugin that does imports from outside the module
        """
        loader = PluginLoader(
            _here("plugins"), "zenoss.withimports", "plugins", CoreImporter()
        )
        plugin = loader.create()
        self.assert_(plugin.get_re() is not None)

    def test_other_pkg(self):
        """
        Import similar dotted names from different packages.
        """
        loader1 = PluginLoader(
            _here("plugins"), "zenoss.noimports", "plugins", CoreImporter()
        )
        loader2 = PluginLoader(
            _here("otherplugins"),
            "zenoss.noimports",
            "plugins",
            CoreImporter(),
        )
        self.assertEqual(loader1.create().MARKER, "abcdefg")
        self.assertEqual(loader2.create().MARKER, "gfedcba")


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(ImportPlugins))
    return suite
