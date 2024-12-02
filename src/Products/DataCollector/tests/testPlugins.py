##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

from os.path import join

from Products.DataCollector.Plugins import CoreLoaderFactory, PackLoaderFactory
from Products.ZenTestCase.BaseTestCase import BaseTestCase


class TestWalker(object):
    """
    instead of walking the filesystem, this walker yields a single tuple
    based on the parameters passed in to the initializer
    """

    def __init__(self, package, path, filename):
        self.package = package
        self.path = path
        self.filename = filename

    def walk(self, package):
        assert package == self.package
        yield join(package, self.path), [], [self.filename]


class BasePluginTest(BaseTestCase):
    def runTest(self):
        loaders = list(self.factory.genLoaders(self.package, "plugins"))
        self.assertEqual(1, len(loaders))
        self.assertEqual(self.package, loaders[0].package)
        self.assertEqual(self.modPath, loaders[0].modPath)
        self.assertEqual(self.pluginName, loaders[0].pluginName)


class CorePluginTest(BasePluginTest):
    "test the conventions used for core plugins"

    def afterSetUp(self):
        super(CorePluginTest, self).afterSetUp()
        self.package = "/usr/local/zenoss/Products/DataCollector/plugins"
        walker = TestWalker(self.package, "zenoss/cmd", "df.py")
        self.factory = CoreLoaderFactory(walker)
        self.pluginName = "zenoss.cmd.df"
        self.modPath = self.pluginName


class EggPackPluginTest(BasePluginTest):
    """
    test the conventions used for zenpack plugins against a simulated
    egg-installed zenpack
    """

    def afterSetUp(self):
        super(EggPackPluginTest, self).afterSetUp()
        self.package = (
            "/usr/local/zenoss/ZenPacks"
            "/ZenPacks.zenoss.LinuxMonitor-1.0.0-py2.4.egg"
            "/ZenPacks/zenoss/LinuxMonitor/modeler/plugins"
        )
        walker = TestWalker(self.package, "zenoss/cmd/linux", "cpuinfo.py")
        modPathPrefix = "ZenPacks.zenoss.LinuxMonitor.modeler.plugins"
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = "zenoss.cmd.linux.cpuinfo"
        self.modPath = ".".join([modPathPrefix, self.pluginName])


class LinkPackPluginTest(BasePluginTest):
    """
    test the conventions used for zenpack plugins against a simulated
    link-installed zenpack
    """

    def afterSetUp(self):
        super(LinkPackPluginTest, self).afterSetUp()
        self.package = (
            "/home/zenoss/working_copies/enterprise_zenpacks"
            "/ZenPacks.zenoss.AixMonitor/ZenPacks/zenoss"
            "/AixMonitor/modeler/plugins/zenoss/cmd/aix"
        )
        walker = TestWalker(self.package, "zenoss/cmd/aix", "lslpp.py")
        modPathPrefix = "ZenPacks.zenoss.AixMonitor.modeler.plugins"
        self.factory = PackLoaderFactory(walker, modPathPrefix)
        self.pluginName = "zenoss.cmd.aix.lslpp"
        self.modPath = ".".join([modPathPrefix, self.pluginName])
        self.lastModName = "plugins"


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CorePluginTest))
    suite.addTest(unittest.makeSuite(EggPackPluginTest))
    suite.addTest(unittest.makeSuite(LinkPackPluginTest))
    return suite
