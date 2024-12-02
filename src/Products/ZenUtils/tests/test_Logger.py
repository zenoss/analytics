##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import mock
import unittest

from ..Logger import getLogger

PATH = {"src": "Products.ZenUtils.Logger"}


class TestGetLogger(unittest.TestCase):
    """Test the getLogger function."""

    def setUp(self):
        self.__patcher = mock.patch(
            "{}.logging".format(PATH["src"]), autospec=True,
        )
        self.logging = self.__patcher.start()
        self.addCleanup(self.__patcher.stop)

    def test_no_class_given(self):
        log = getLogger("testing")
        self.logging.getLogger.assert_called_once_with("zen.testing")
        self.assertEqual(self.logging.getLogger.return_value, log)

    def test_no_class_given_dotted_app(self):
        log = getLogger("app.thing")
        self.logging.getLogger.assert_called_once_with("zen.app.thing")
        self.assertEqual(self.logging.getLogger.return_value, log)

    def test_with_cls_module(self):
        import Products.ZenUtils
        log = getLogger("app", Products.ZenUtils)
        self.logging.getLogger.assert_called_once_with("zen.app.ZenUtils")
        self.assertEqual(self.logging.getLogger.return_value, log)

    def test_with_cls_classic_class(self):
        class Bar:
            pass
        log = getLogger("app", Bar)
        self.logging.getLogger.assert_called_once_with("zen.app.Bar")
        self.assertEqual(self.logging.getLogger.return_value, log)

    def test_with_cls_newclass_class(self):
        class Foo(object):
            pass
        log = getLogger("app", Foo)
        self.logging.getLogger.assert_called_once_with("zen.app.Foo")
        self.assertEqual(self.logging.getLogger.return_value, log)

    def test_with_cls_object(self):
        class Foo(object):
            pass
        foo = Foo()
        log = getLogger("app", foo)
        self.logging.getLogger.assert_called_once_with("zen.app.Foo")
        self.assertEqual(self.logging.getLogger.return_value, log)
