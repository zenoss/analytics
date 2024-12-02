##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from mock import Mock, patch, ANY
from unittest import TestCase

from Products.ZenHub.pinger import PingZenHub

PATH = {"src": "Products.ZenHub.pinger"}


class PingZenHubTest(TestCase):
    """Test the PingZenHub class."""

    def setUp(t):
        t.zenhub = Mock()
        t.client = Mock()
        t.interval = 30
        # Patch external dependencies
        needs_patching = ["task", "logging"]
        t.patchers = {}
        for target in needs_patching:
            patched = patch(
                "{src}.{target}".format(target=target, **PATH),
                autospec=True,
            )
            t.patchers[target] = patched
            name = target.rpartition(".")[-1]
            setattr(t, name, patched.start())
            t.addCleanup(patched.stop)

        t.pzh = PingZenHub(t.zenhub, interval=t.interval)

    def test_start(t):
        t.pzh.start()

        loop = t.task.LoopingCall.return_value
        loop.start.assert_called_once_with(t.interval, now=False)

    def test_stop_before_start(t):
        t.pzh.stop()

        loop = t.task.LoopingCall.return_value
        t.assertFalse(loop.called)

    def test_stop_after_start(t):
        t.pzh.start()
        t.pzh.stop()

        loop = t.task.LoopingCall.return_value
        loop.stop.assert_called_once_with()

    def test_call(t):
        t.pzh()
        t.zenhub.ping.assert_called_once_with()

    def test___call__failed(t):
        logger = t.logging.getLogger.return_value
        ex = ValueError("boom")
        t.zenhub.ping.side_effect = ex

        t.pzh()

        logger.error.assert_called_once_with(ANY, ex)
