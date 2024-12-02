##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from unittest import TestCase

from mock import MagicMock, patch

from ..task import requires, DMD
from ..zenjobs import app


class DMDTest(TestCase):
    """Test the DMD mixin class."""

    def setUp(self):
        log = logging.getLogger()
        log.setLevel(logging.FATAL + 1)

    def tearDown(self):
        log = logging.getLogger()
        log.setLevel(logging.NOTSET)

    @app.task(bind=True, base=requires(DMD))
    def dmd_task_rw(self):
        pass

    @app.task(bind=True, base=requires(DMD), dmd_read_only=True)
    def dmd_task_ro(self):
        pass

    def test_rw_defaults(t):
        t.assertIsInstance(t.dmd_task_rw, DMD)
        t.assertFalse(t.dmd_task_rw.dmd_read_only)
        t.assertIsNone(t.dmd_task_rw.dmd)

    def test_ro_defaults(t):
        t.assertIsInstance(t.dmd_task_ro, DMD)
        t.assertTrue(t.dmd_task_ro.dmd_read_only)
        t.assertIsNone(t.dmd_task_ro.dmd)

    @patch("Products.Jobber.task.dmd.transaction")
    def test_rw(t, transaction_):
        db = MyMagicMock()
        app.db = db
        try:
            t.dmd_task_rw()
            transaction_.abort.assert_not_called()
            transaction_.commit.assert_called_with()
        finally:
            del app.db

    @patch("Products.Jobber.task.dmd.transaction")
    def test_ro(t, transaction_):
        db = MyMagicMock()
        app.db = db
        try:
            t.dmd_task_ro()
            transaction_.commit.assert_not_called()
            transaction_.abort.assert_called_with()
        finally:
            del app.db


class MyMagicMock(MagicMock):

    def __of__(self, *args, **kw):
        return self
