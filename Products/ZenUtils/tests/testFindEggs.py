##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os

from contextlib import contextmanager

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.zenpack import ZenPackCmd
from Products.ZenUtils.path import zenPath


@contextmanager
def mockListdir(name, version):
    """Replace os.listdir with a mock.
    """
    eggname = "%s-%s-py2.7.egg" % (name, version)
    def listdir(dirname):
        if dirname.endswith(".ZenPacks"):
            return [eggname]
        return []
    original = os.listdir
    os.listdir = listdir
    yield zenPath(".ZenPacks", eggname)
    os.listdir = original


class TestFindEggs(BaseTestCase):
    """Test the _findEggs routine."""

    def test001_WrongName(self):
        """The egg names are different.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test001", "1.0.0") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Looking", "1.0.0")
            self.assertEquals(result, [])

    def test002_WrongVersion(self):
        """Same name, different versions.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test002", "1.0.0") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Test002", "1.2.0")
            self.assertEquals(result, [])

    def test003_Found(self):
        """The egg is found.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test003", "1.0.0") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Test003", "1.0.0")
            self.assertEquals(result, [eggPath])

    def test004_DashedVersion(self):
        """The egg has a dash in its version.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test004", "1.0.0_test") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Test004", "1.0.0-test")
            self.assertEquals(result, [eggPath])

    def test005_UnderscoreVersion(self):
        """The egg has an underscore in its version.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test005", "1.0.0_unstable") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Test005", "1.0.0_unstable")
            self.assertEquals(result, [eggPath])

    def test006_VersionWithText(self):
        """The egg has text but no dash in its version.
        """
        zpc = ZenPackCmd()
        with mockListdir("ZenPacks.zenoss.Test006", "1.0.0dev") as eggPath:
            result = zpc._findEggs("ZenPacks.zenoss.Test006", "1.0.0dev")
            self.assertEquals(result, [eggPath])
