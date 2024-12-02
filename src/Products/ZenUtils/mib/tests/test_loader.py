# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import mock
import os

from unittest import TestCase

# from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.mib import MIBLoader, ModuleManager
from Products.ZenUtils.mib.smidump import SMIDump
from Products.ZenUtils.mib.loader import (
    add_mib, broadcast, eval_python_literal, file_writer, iterate, transform
)


class CoroutineMock(object):

    def __init__(self):
        self.received = []

    def send(self, item):
        self.received.append(item)


class TestAddMib(TestCase):
    """
    """

    def test_once(self):
        manager = mock.Mock()
        organizer = object()
        mib = object()
        routine = add_mib(manager, organizer)
        routine.send(mib)
        manager.add.assert_called_with(mib, organizer)

    def test_twice(self):
        manager = mock.Mock()
        organizer = object()
        first_mib = object()
        second_mib = object()
        routine = add_mib(manager, organizer)
        routine.send(first_mib)
        routine.send(second_mib)
        manager.add.assert_has_calls([
            mock.call(first_mib, organizer),
            mock.call(second_mib, organizer)
        ])


class TestTransform(TestCase):

    def test_simple(self):
        target = CoroutineMock()
        routine = transform(
            lambda x: "You're the {}.".format(x), target
        )
        routine.send("bomb")
        self.assertEqual(len(target.received), 1)
        self.assertEqual(target.received[0], "You're the bomb.")

    def test_restructure(self):
        target = CoroutineMock()
        routine = transform(lambda x, y: y, target)
        routine.send(["a", "b"])
        self.assertEqual(len(target.received), 1)
        self.assertEqual(target.received[0], "b")


class TestBroadcast(TestCase):

    def test_one_target(self):
        target = CoroutineMock()
        routine = broadcast(target)
        item = object()
        routine.send(item)
        self.assertEqual(len(target.received), 1)
        self.assertEqual(target.received[0], item)

    def test_n_targets(self):
        targets = [
            CoroutineMock(),
            CoroutineMock(),
            CoroutineMock(),
            CoroutineMock(),
        ]
        routine = broadcast(targets)
        item = object()
        routine.send(item)
        for target in targets:
            self.assertEqual(len(target.received), 1)
            self.assertEqual(target.received[0], item)


class TestIterate(TestCase):

    def test_empty(self):
        target = CoroutineMock()
        routine = iterate(lambda x: [], target)
        routine.send([])
        self.assertEqual(len(target.received), 0)

    def test_not_empty(self):
        target = CoroutineMock()
        routine = iterate(lambda x: x, target)
        routine.send([1, 2, 3])
        self.assertEqual(len(target.received), 3)
        self.assertEqual(target.received[0], 1)
        self.assertEqual(target.received[1], 2)
        self.assertEqual(target.received[2], 3)

    def test_not_iterable(self):
        target = CoroutineMock()
        routine = iterate(lambda x: 5, target)
        with self.assertRaises(TypeError):
            routine.send([1, 2, 3])


class TestFileWriter(TestCase):

    def test_ok(self):
        path = "/a/b/c"
        fname, contents = "out", "some content"
        m = mock.mock_open()
        with mock.patch("__builtin__.open", m, create=True):
            routine = file_writer(path)
            routine.send((fname, contents))

        m.assert_called_with(os.path.join(path, fname), "w")
        fd = m()
        fd.write.assert_called_with(contents)
        self.assertTrue(fd.flush.called)

    def test_exception(self):
        path = "/no/such"
        fname, contents = "file", "some content"
        m = mock.mock_open()
        m.side_effect = IOError(
            "[Error 2] No such file or directory: %s"
            % os.path.join(path, fname)
        )
        with mock.patch("__builtin__.open", m, create=True):
            routine = file_writer(path)
            with self.assertRaises(IOError):
                routine.send((fname, contents))


class TestEvalPythonLiteral(TestCase):

    def test_dict(self):
        literal = """{"a": 1}"""
        expected = {"a": 1}
        target = CoroutineMock()
        routine = eval_python_literal(target)
        routine.send(literal)
        self.assertEqual(len(target.received), 1)
        self.assertEqual(target.received[0], expected)

    def test_varied(self):
        literal = (
            "{\n"
            "\t'a': 1,\n"
            "\t'b': [1, 2, 'hi', 4, 5.5],\n"
            "\t'c': r'pitón',\n"
            "\t'd': [\n"
            "\t\t{'A': 'hello'},\n"
            "\t\t{'B': 'world'},\n"
            "\t]\n"
            "}"
        )
        expected = {
            "a": 1, "b": [1, 2, "hi", 4, 5.5], "c": "pit\xc3\xb3n",
            "d": [{"A": "hello"}, {"B": "world"}]
        }
        target = CoroutineMock()
        routine = eval_python_literal(target)
        routine.send(literal)
        self.assertEqual(len(target.received), 1)
        self.assertEqual(target.received[0], expected)

    def test_multiple_literals(self):
        literals = (
            "[1,2,3]\n"
            "5"
        )
        target = CoroutineMock()
        routine = eval_python_literal(target)
        with self.assertRaises(SyntaxError):
            routine.send(literals)

    def test_statement(self):
        data = "FILENAME = 'afile'"
        target = CoroutineMock()
        routine = eval_python_literal(target)
        with self.assertRaises(SyntaxError):
            routine.send(data)


class TestMIBLoader(TestCase):

    def test_load_only(self):
        manager = mock.Mock(spec=ModuleManager)
        organizer = object()
        dump = mock.Mock(spec=SMIDump)
        dump.definitions = [
            "{'name': 'MIB1'}", "{'name': 'MIB2'}", "{'name': 'MIB3'}"
        ]
        with MIBLoader(manager, organizer) as loader:
            loader.load(dump)
        manager.add.assert_has_calls([
            mock.call({"name": "MIB1"}, organizer),
            mock.call({"name": "MIB2"}, organizer),
            mock.call({"name": "MIB3"}, organizer)
        ])

    def test_save_and_load(self):
        manager = mock.Mock(spec=ModuleManager)
        organizer = object()
        dump = mock.Mock(spec=SMIDump)
        dump.files = [("mib", "MIB1 MIB2 MIB3")]
        dump.definitions = [
            "{'name': 'MIB1'}", "{'name': 'MIB2'}", "{'name': 'MIB3'}"
        ]
        path = "/a/b/c"
        m = mock.mock_open()

        with mock.patch("__builtin__.open", m, create=True):
            with MIBLoader(manager, organizer, savepath=path) as loader:
                loader.load(dump)

        m.assert_called_with("/a/b/c/mib.py", "w")
        fd = m()
        fd.write.assert_called_with("MIB1 MIB2 MIB3")

        manager.add.assert_has_calls([
            mock.call({"name": "MIB1"}, organizer),
            mock.call({"name": "MIB2"}, organizer),
            mock.call({"name": "MIB3"}, organizer)
        ])
