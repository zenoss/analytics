##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging

from unittest import TestCase

from ..jobs.subprocess import (
    getLogFormattingContext,
    LogFormatterContext,
    null_context,
)
from ..utils.log import TaskLogFileHandler
from .utils import LoggingLayer


class LogFormatterContextTest(TestCase):
    """Test the LogFormatterContext class."""

    layer = LoggingLayer

    def setUp(t):
        t.layer.manager.loggerDict.clear()
        t.formatter = logging.Formatter("%(message)s")
        t.handler = logging.NullHandler()

    def test_usage(t):
        ctx = LogFormatterContext(t.handler, t.formatter)
        with ctx():
            pass

    def test_getLogFormattingContext_notask(t):
        ctx = getLogFormattingContext()
        t.assertIs(ctx, null_context)

    def test_getLogFormattingContext_hastask(t):
        zen = logging.getLogger("zen")
        handler = TaskLogFileHandler("/tmp/logformattercontext.log")
        zen.addHandler(handler)

        ctx = getLogFormattingContext()
        t.assertIsInstance(ctx, (LogFormatterContext,))
