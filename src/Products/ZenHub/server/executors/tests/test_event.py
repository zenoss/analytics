##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from mock import DEFAULT, MagicMock, Mock, patch
from twisted.internet import defer
from twisted.python.failure import Failure
from unittest import TestCase

from Products.ZenHub.server.service import ServiceCall
from Products.Zuul.interfaces import IDataRootFactory

from ..event import SendEventExecutor

PATH = {"src": "Products.ZenHub.server.executors.event"}


class SendEventExecutorTest(TestCase):
    """Test the SendEventExecutor class."""

    maxDiff = None

    def _copy_notify_args(self, data, eventtype):
        self.notify_calls.append((dict(data), eventtype))
        return DEFAULT

    def setUp(self):
        names_to_patch = [
            "getUtility",
            "getattr",
        ]
        for name in names_to_patch:
            patcher = patch("{src}.{name}".format(src=PATH["src"], name=name))
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

        self.zem = MagicMock(spec=["__class__", "sendEvent", "sendEvents"])
        self.dmd_factory = self.getUtility.return_value
        self.dmd_factory.return_value.ZenEventManager = self.zem

        self.name = "event"
        self.executor = SendEventExecutor(self.name)

    def test_create(self):
        result = SendEventExecutor.create("test")
        self.assertIsInstance(result, SendEventExecutor)
        self.assertEqual(result.name, "test")

    def test_initialization(self):
        self.getUtility.assert_called_once_with(IDataRootFactory)
        self.assertEqual(self.name, self.executor.name)

    def test_start(self):
        """noop, required for interface"""
        reactor = Mock(name="reactor")
        self.executor.start(reactor)

    def test_stop(self):
        """noop, required for interface"""
        self.executor.stop()

    def test_wrong_method(self):
        servicecall = ServiceCall(
            monitor="localhost",
            service="EventService",
            method="badmethod",
            args=["event"],
            kwargs={},
        )

        handler = Mock()
        dfr = self.executor.submit(servicecall)
        dfr.addErrback(handler)

        self.assertEqual(len(handler.mock_calls), 1)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, TypeError)
        self.assertRegexpMatches(str(f.value), ".*badmethod.*")

        self.zem.sendEvent.assert_not_called()
        self.zem.sendEvents.assert_not_called()
        self.getattr.assert_not_called()

    def test_missing_method(self):
        servicecall = ServiceCall(
            monitor="localhost",
            service="EventService",
            method="sendEvent",
            args=["event"],
            kwargs={},
        )

        self.getattr.return_value = None

        handler = Mock()
        dfr = self.executor.submit(servicecall)
        dfr.addErrback(handler)

        self.getattr.assert_called_once_with(
            self.zem,
            servicecall.method,
            None,
        )
        self.assertEqual(len(handler.mock_calls), 1)

        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, AttributeError)
        self.assertRegexpMatches(str(f.value), ".*sendEvent.*")

        self.zem.sendEvent.assert_not_called()
        self.zem.sendEvents.assert_not_called()

    def test_sendEvent(self):
        servicecall = ServiceCall(
            monitor="localhost",
            service="EventService",
            method="sendEvent",
            args=["event"],
            kwargs={},
        )

        sendEvent = self.zem.sendEvent
        sendEvents = self.zem.sendEvents
        self.getattr.return_value = sendEvent

        dfr = self.executor.submit(servicecall)

        self.assertIsInstance(dfr, defer.Deferred)
        self.getattr.assert_called_once_with(
            self.zem,
            servicecall.method,
            None,
        )
        self.assertEqual(sendEvent.return_value, dfr.result)
        sendEvent.assert_called_once_with("event")
        sendEvents.assert_not_called()

    def test_sendEvents(self):
        servicecall = ServiceCall(
            monitor="localhost",
            service="EventService",
            method="sendEvents",
            args=[["event"]],
            kwargs={},
        )

        sendEvent = self.zem.sendEvent
        sendEvents = self.zem.sendEvents
        self.getattr.return_value = sendEvents

        dfr = self.executor.submit(servicecall)

        self.assertIsInstance(dfr, defer.Deferred)
        self.getattr.assert_called_once_with(
            self.zem,
            servicecall.method,
            None,
        )
        self.assertEqual(sendEvents.return_value, dfr.result)
        sendEvents.assert_called_once_with(["event"])
        sendEvent.assert_not_called()

    def test_exception_from_service(self):
        servicecall = ServiceCall(
            monitor="localhost",
            service="EventService",
            method="sendEvent",
            args=[],
            kwargs={},
        )

        error = ValueError("boom")
        sendEvent = self.zem.sendEvent
        sendEvents = self.zem.sendEvents
        self.getattr.return_value = sendEvent
        sendEvent.side_effect = error

        handler = Mock()
        dfr = self.executor.submit(servicecall)
        dfr.addErrback(handler)

        self.assertEqual(len(handler.mock_calls), 1)

        self.getattr.assert_called_once_with(
            self.zem,
            servicecall.method,
            None,
        )
        f = handler.call_args[0][0]
        self.assertIsInstance(f, Failure)
        self.assertIsInstance(f.value, ValueError)
        self.assertEqual(str(f.value), "boom")

        sendEvent.assert_called_once_with()
        sendEvents.assert_not_called()
