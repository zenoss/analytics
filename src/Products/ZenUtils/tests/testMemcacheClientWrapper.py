##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import memcache
import mock
import types
import unittest
import uuid

from contextlib import contextmanager

from Products.ZenUtils.memcacheClientWrapper import createModule


@contextmanager
def mockMemcacheClient():
    """ Replace memcache.Client class with a mock """

    class MockClient(object):
        instances = []

        def __init__(self, *args, **kwargs):
            self.initArgs = args
            self.initKwargs = kwargs
            MockClient.instances.append(self)

    original = memcache.Client
    memcache.Client = MockClient
    yield MockClient
    memcache.Client = original


def mockAdapter():
    """ Replace relstorage.adapter with a mock class """
    adapter = mock.Mock()
    adapter.packundo = {}
    return adapter


class TestMemcacheClientWrapper(unittest.TestCase):
    """ Tests the memcacheClientWrapper module """

    def testModuleImportStatic(self):
        moduleName = "foo"
        kwargs = {"foo": 1, "bar": 2}
        createModule(moduleName, **kwargs)
        try:
            import foo
        except ImportError:
            self.fail("Could not import module")
        self.assertIsInstance(foo, types.ModuleType)

    def testModuleImportDynamic(self):
        moduleName = str(uuid.uuid4())
        kwargs = {"foo": 1, "bar": moduleName}
        createModule(moduleName, **kwargs)
        module = __import__(moduleName, {}, {}, [])
        self.assertIsInstance(module, types.ModuleType)
        self.assertEqual(module.__name__, moduleName)

    def testModuleContainsClientClass(self):
        moduleName = str(uuid.uuid4())
        kwargs = {"foo": 1, "bar": moduleName}
        createModule(moduleName, **kwargs)
        module = __import__(moduleName, {}, {}, [])
        self.assertTrue("Client" in module.__dict__)
        # module.Client is a class
        self.assertTrue(type(module.Client) is type)

    def testClientOveridesInitializer(self):
        moduleName = str(uuid.uuid4())
        kwargs = {"foo": 1, "bar": moduleName}
        args = (1, 2, "woot")
        with mockMemcacheClient():
            createModule(moduleName, **kwargs)
            module = __import__(moduleName, {}, {}, [])
            client = module.Client(*args)
        self.assertEqual(client.initArgs, args)
        self.assertEqual(client.initKwargs, kwargs)

    def testClientArgOveride(self):
        moduleName = str(uuid.uuid4())
        moduleKwargs = {"foo": 1, "bar": moduleName}
        initializerKwargs = {"foo": 11, "baz": None}
        with mockMemcacheClient():
            createModule(moduleName, **moduleKwargs)
            module = __import__(moduleName, {}, {}, [])
            client = module.Client(**initializerKwargs)
        expected = dict(moduleKwargs, **initializerKwargs)
        self.assertEqual(client.initKwargs, expected)
