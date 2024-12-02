##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import os, sys

if __name__ == "__main__":
    execfile(os.path.join(sys.path[0], "framework.py"))

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRelations.ZItem import ZItem


class TestZItem(BaseTestCase):
    def testGetId(self):
        zitem = ZItem()
        zitem.id = "testid"
        self.assertEquals("testid", zitem.getId())

    def testTitleOrId(self):
        zitem = ZItem()
        zitem.id = "testid"
        self.assertEquals("testid", zitem.titleOrId())
        self.assertEquals("testid", zitem.title_or_id())
        zitem.title = "testtitle"
        self.assertEquals("testtitle", zitem.titleOrId())
        self.assertEquals("testtitle", zitem.title_or_id())


def test_suite():
    from unittest import TestSuite, makeSuite

    suite = TestSuite()
    suite.addTest(makeSuite(TestZItem))
    return suite


if __name__ == "__main__":
    framework()
