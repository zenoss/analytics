##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import time
import uuid

from unittest import TestCase

from ..events import (
    ServiceCallReceived,
    ServiceCallStarted,
    ServiceCallCompleted,
)
from ..priority import ServiceCallPriority
from ..utils import subTest


class ServiceCallReceivedTest(TestCase):
    """Test the ServiceCallReceived class."""

    def test_nominal(self):
        evid = uuid.uuid4()
        now = time.time()

        _ = ServiceCallReceived(
            id=evid,
            monitor="localhost",
            service="PingPerf",
            method="getPingStuff",
            args=[],
            kwargs={},
            timestamp=now,
            queue="default",
            priority=ServiceCallPriority.OTHER,
        )

    def test_no_extra_init_args(self):
        args = ("worker", "attempts", "error", "retry", "result", "foo")
        for arg in args:
            with subTest(arg=arg):
                with self.assertRaises(TypeError):
                    ServiceCallReceived(**{arg: None})


class ServiceCallStartedTest(TestCase):
    """Test the ServiceCallStarted class."""

    def test_nominal(self):
        evid = uuid.uuid4()
        now = time.time()

        _ = ServiceCallStarted(
            id=evid,
            monitor="localhost",
            service="PingPerf",
            method="getPingStuff",
            args=[],
            kwargs={},
            timestamp=now,
            queue="default",
            priority=ServiceCallPriority.OTHER,
            worker="default_0",
            attempts=1,
        )


    def test_no_extra_init_args(self):
        tests = ("error", "retry", "result", "foo")
        for test in tests:
            with subTest(test=test):
                args = {"attempts": 1, test: None}
                with self.assertRaises(TypeError):
                    ServiceCallStarted(**args)


class ServiceCallCompletedTest(TestCase):
    """Test the ServiceCallCompleted class."""

    def setUp(self):
        self.evid = uuid.uuid4()
        self.now = time.time()
        self.base = {
            "id": self.evid,
            "monitor": "localhost",
            "service": "PingPerf",
            "method": "getPingStuff",
            "args": [],
            "kwargs": {},
            "timestamp": self.now,
            "queue": "default",
            "priority": ServiceCallPriority.OTHER,
            "worker": "default_0",
            "attempts": 1,
        }

    def test_mismatched_arguments(self):
        exc = RuntimeError()
        result = 10
        tests = (
            {},
            {"error": exc, "retry": exc},
            {"result": result, "error": exc, "retry": exc},
            {"error": exc, "result": result},
        )
        for sample in tests:
            args = dict(self.base)
            args.update(**sample)
            with subTest(args=args):
                with self.assertRaises(TypeError):
                    ServiceCallCompleted(**args)

    def test_nominal_init_failure(self):
        exc = RuntimeError()
        self.base["error"] = exc
        event = ServiceCallCompleted(**self.base)
        self.assertEqual(1, event.attempts)
        self.assertIs(exc, event.error)

    def test_nominal_init_retry(self):
        exc = RuntimeError()
        self.base["retry"] = exc
        event = ServiceCallCompleted(**self.base)
        self.assertEqual(1, event.attempts)
        self.assertIs(exc, event.retry)

    def test_nominal_init_success(self):
        result = 10
        self.base["result"] = result
        event = ServiceCallCompleted(**self.base)
        self.assertEqual(1, event.attempts)
        self.assertIs(result, event.result)

    def test_no_extra_init_args(self):
        with self.assertRaises(TypeError):
            ServiceCallCompleted(attempts=1, foo=10)
