##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from unittest import TestCase
from mock import create_autospec

from ..router import ServiceCallRouter
from ..service import ServiceCall
from ..utils import subTest


class ServiceCallRouterTest(TestCase):
    """Test the ServiceCallRouter class."""

    def setUp(self):
        self.routes = {
            "m1": {
                "s1": "e1",
            },
            "foo": {
                "*": "e3",
            },
            "*": {
                "s1": "e2",
                "*": "e4",
            },
        }
        self.router = ServiceCallRouter(self.routes)

    def test_get(self):
        tests = (
            ("s1", "foo", "e3"),
            ("s1", "m1", "e1"),
            ("s1", "bar", "e2"),
            ("s2", "m1", "e4"),
            ("s2", "foo", "e3"),
            ("s2", "bar", "e4"),
        )
        call = create_autospec(ServiceCall)
        for service, method, expected in tests:
            call.service = service
            call.method = method
            with subTest(service=service, method=method):
                actual = self.router.get(call)
                self.assertEqual(expected, actual)

    def test_get_default(self):
        default = "default_value"
        tests = (
            ("s1", "foo", "e3"),
            ("s1", "m1", "e1"),
            ("s1", "bar", "e2"),
            ("s2", "m1", default),
        )
        call = create_autospec(ServiceCall)
        for service, method, expected in tests:
            call.service = service
            call.method = method
            with subTest(service=service, method=method):
                actual = self.router.get(call, default)
                self.assertEqual(expected, actual)

    def test___getitem__(self):
        tests = (
            ("s1", "foo", "e3"),
            ("s1", "m1", "e1"),
            ("s1", "bar", "e2"),
            ("s2", "m1", "e4"),
            ("s2", "foo", "e3"),
            ("s2", "bar", "e4"),
        )
        call = create_autospec(ServiceCall)
        for service, method, expected in tests:
            call.service = service
            call.method = method
            with subTest(service=service, method=method):
                actual = self.router[call]
                self.assertEqual(expected, actual)

    def test___iter__(self):
        expected = {
            (("s1", "m1"), "e1"),
            (("*", "foo"), "e3"),
            (("s1", "*"), "e2"),
            (("*", "*"), "e4"),
        }
        result = tuple(self.router)
        self.assertEqual(len(expected), len(result))
        self.assertSetEqual(expected, set(result))

    def test___len__(self):
        expected = 4
        actual = len(self.router)
        self.assertEqual(expected, actual)


class ServiceCallRouterFromConfigTest(TestCase):
    """Test the ServiceCallRouter.from_config function."""

    def test_from_config_nominal_input(self):
        config = {
            "s1:m1": "e1",
            "s1:*": "e2",
            "*:m1": "e3",
            "*:*": "e4",
        }
        expected = {
            (("s1", "m1"), "e1"),
            (("s1", "*"), "e2"),
            (("*", "m1"), "e3"),
            (("*", "*"), "e4"),
        }
        router = ServiceCallRouter.from_config(config)
        actual = set(router)
        self.assertSetEqual(expected, actual)

    def test_from_config_missing_default(self):
        config = {
            "s1:m1": "e1",
            "s1:*": "e2",
            "*:m1": "e3",
        }
        message = r"Missing required '\*:\*' route"
        with self.assertRaisesRegexp(ValueError, message):
            ServiceCallRouter.from_config(config)
