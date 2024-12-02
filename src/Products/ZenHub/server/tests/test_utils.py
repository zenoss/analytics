##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

from mock import call, Mock, patch
from unittest import TestCase

from ..utils import (
    TCPVersion,
    tcp,
    TCPDescriptor,
    import_name,
    import_service_class,
    UnknownServiceError,
)

PATH = {"src": "Products.ZenHub.server.utils"}


class TCPVersionTest(TestCase):
    """Test the TCPVersion class."""

    @patch("{src}.ipv6_available".format(**PATH), autospec=True)
    def test_version_ip4(self, _ipv6_available):
        _ipv6_available.return_value = False
        _tcp = TCPVersion()
        self.assertEqual("tcp", _tcp.version)

    @patch("{src}.ipv6_available".format(**PATH), autospec=True)
    def test_version_ipv6(self, _ipv6_available):
        _ipv6_available.return_value = True
        _tcp = TCPVersion()
        self.assertEqual("tcp6", _tcp.version)

    def test_tcp(self):
        self.assertIsInstance(tcp, TCPVersion)


class TCPDescriptorTest(TestCase):
    """Test the TCPDescriptor class."""

    def test_with_port(self):
        port = 6543
        expected = "{}:port={}".format(tcp.version, port)
        actual = TCPDescriptor.with_port(port)
        self.assertEqual(expected, actual)


class ImportNameTest(TestCase):
    """Test the import_name function."""

    def setUp(self):
        self.importlib_patcher = patch(
            "{src}.importlib".format(**PATH),
            autospec=True,
        )
        self.importlib = self.importlib_patcher.start()
        self.addCleanup(self.importlib_patcher.stop)

    def test_nominal_path_only(self):
        module = Mock(spec=["d"])
        self.importlib.import_module.return_value = module
        path = "a.b.c.d"

        item = import_name(path)

        self.assertIs(module.d, item)
        self.importlib.import_module.assert_called_once_with("a.b.c")

    def test_nominal_path_and_name(self):
        module = Mock(spec=["d"])
        self.importlib.import_module.return_value = module
        path = "a.b.c"
        name = "d"

        item = import_name(path, name)

        self.assertIs(module.d, item)
        self.importlib.import_module.assert_called_once_with("a.b.c")

    def test_badpath(self):
        error = ImportError()
        self.importlib.import_module.side_effect = error
        path = "foo.bar.baz"

        with self.assertRaises(ImportError):
            import_name(path)

    def test_missing_name(self):
        module = Mock(spec=["d"])
        self.importlib.import_module.return_value = module
        path = "a.b.c"
        name = "foo"

        with self.assertRaises(ImportError):
            import_name(path, name)

        self.importlib.import_module.assert_called_once_with("a.b.c")


class ImportServiceClassTest(TestCase):
    """Test the import_service_class function."""

    def setUp(self):
        self.import_name_patcher = patch(
            "{src}.import_name".format(**PATH),
            autospec=True,
        )
        self.import_name = self.import_name_patcher.start()
        self.addCleanup(self.import_name_patcher.stop)

    def test_nominal_abbreviated_path(self):
        cls = Mock()
        self.import_name.side_effect = (ImportError(), cls)
        name = "ModelerService"
        path = "ModelerService"
        fullpath = "Products.ZenHub.services.ModelerService"

        service = import_service_class(path)

        self.assertIs(cls, service)
        self.import_name.assert_has_calls(
            (
                call(path, name),
                call(fullpath, name),
            )
        )

    def test_nominal_full_path(self):
        cls = Mock()
        self.import_name.return_value = cls
        name = "PythonConfig"
        path = "ZenPacks.zenoss.PythonCollector.services.PythonConfig"

        service = import_service_class(path)

        self.assertIs(cls, service)
        self.import_name.assert_called_once_with(path, name)

    def test_bad_path(self):
        error = ImportError("boom")
        self.import_name.side_effect = (error, error)
        name = "Baz"
        path = "Foo.Bar.Baz"

        with self.assertRaises(UnknownServiceError):
            import_service_class(path)

        self.import_name.assert_has_calls(
            (
                call(path, name),
                call("Products.ZenHub.services.Foo.Bar.Baz", name),
            )
        )
