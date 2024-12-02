##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import types
from unittest import TestCase
from zope.interface import implementer

from ..broker import (
    IUnjellyable,
    ZenBroker,
    ZenPBClientFactory,
    ZenPBServerFactory,
    zenSecurityOptions,
    ZenSecurityOptions,
)


class ZenSecurityOptionsTest(TestCase):
    """Test the ZenSecurityOptions class."""

    def setUp(t):
        t.options = ZenSecurityOptions()

    def test_global_object(t):
        t.assertIsInstance(zenSecurityOptions, ZenSecurityOptions)

    def test_allow_all_types(t):
        # Just a sample of type names.
        typenames = (
            "__builtin__.dict",
            "remote",
            "Products.ZenHub.services.ProcessConfig.ProcessProxy",
        )
        for typename in typenames:
            t.assertTrue(t.options.isTypeAllowed(typename))

    def test_allow_all_modules(t):
        # Just a sample of module names
        modnames = (
            "__main__",
            "zope",
            "Products.ZenHub",
            "ZenPacks.zenoss.PythonCollector.services.PythonConfig",
        )
        for modname in modnames:
            t.assertTrue(t.options.isTypeAllowed(modname))

    def test_disallow_arbitrary_class(t):
        classes = (
            types.ClassType("foo", (), {}),
            types.TypeType("bar", (), {}),
        )
        for cls in classes:
            t.assertFalse(IUnjellyable.implementedBy(cls))
            t.assertFalse(t.options.isClassAllowed(cls))

    def test_allow_unjellyable_class(t):
        classes = (
            implementer(IUnjellyable)(types.ClassType("foo", (), {})),
            implementer(IUnjellyable)(types.TypeType("bar", (), {})),
        )
        for cls in classes:
            t.assertTrue(t.options.isClassAllowed(cls))


class ZenBrokerTest(TestCase):
    """Test the ZenBroker class."""

    def setUp(t):
        t.broker = ZenBroker()

    def test_has_security(t):
        t.assertIsInstance(t.broker.security, ZenSecurityOptions)
        t.assertEqual(t.broker.security, zenSecurityOptions)


class ZenPBClientFactoryTest(TestCase):
    """Test the ZenPBClientFactory class."""

    def test_has_zenbroker(t):
        t.assertIs(ZenPBClientFactory.protocol, ZenBroker)


class ZenPBServerFactoryTest(TestCase):
    """Test the ZenPBServerFactory class."""

    def test_has_zenbroker(t):
        t.assertIs(ZenPBServerFactory.protocol, ZenBroker)
