##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import contextlib
import importlib
import logging
import sys
import traceback
import types

import six

from Products.ZenUtils.Utils import ipv6_available

from .exceptions import UnknownServiceError

UNSPECIFIED = object()


class TCPVersion(object):
    """Determine the latest available TCP protocol."""

    def __init__(self):
        self.__version = None

    @property
    def version(self):
        if self.__version is None:
            self.__version = "tcp6" if ipv6_available() else "tcp"
        return self.__version


tcp = TCPVersion()


class TCPDescriptor(object):
    """Namespace for building Twisted compatible TCP descriptors."""

    @staticmethod
    def with_port(port):
        return "%s:port=%s" % (tcp.version, port)


def getLogger(cls):
    if isinstance(cls, six.string_types):
        name = cls.split(".")[-1]
    else:
        if isinstance(cls, types.InstanceType):
            cls = cls.__class__
        elif isinstance(cls, types.ModuleType):
            pass  # Avoid matching the next elif statement.
        elif not isinstance(cls, types.TypeType):
            cls = type(cls)
        name = cls.__name__.split(".")[-1]
    return logging.getLogger("zen.zenhub.server.{}".format(name.lower()))


def import_service_class(clspath):
    """Import ZenHub service class specified by clspath.

    Two forms of path are accepted.  Full paths and abbreviated paths that
    assume the class may be found in the Products.ZenHub.services package.

    For services found in Products.ZenHub.services, the following is OK:

        import_service_class("EventService")

    For services defined in other packages, the full path is required:

        import_service_class(
            "ZenPacks.zenoss.PythonCollector.services.PythonConfig",
        )

    :param path: The path to the ZenHub service class
    :returns: The ZenHub service class
    :rtype: Products.ZenHub.HubService
    :raises ImportError: If path does not identify a HubService class.
    """
    try:
        try:
            name = clspath.rsplit(".", 1)[-1]
            return import_name(clspath, name)
        except ImportError:
            fullclspath = "Products.ZenHub.services.%s" % clspath
            return import_name(fullclspath, name)
    except ImportError:
        raise UnknownServiceError(str(clspath))


def import_name(path, name=None):
    """Import the named attribute.

    If name is None, the last 'atom' of path is used as the name.

    E.g. both

        import_name("a.b.c.d")

    and

        import_name("a.b.c", "d")

    are equivalent to

        from a.b.c import d

    :param str path: The path to import
    :param str name: The name to import from path
    :raises ImportError: If the path or name cannot be imported
    """
    if name is None:
        path, name = path.rsplit(".", 1)
    module = importlib.import_module(path)
    obj = getattr(module, name, UNSPECIFIED)
    if obj is UNSPECIFIED:
        raise ImportError("Cannot import name %s from %s" % (name, path))
    return obj


@contextlib.contextmanager
def subTest(**params):
    try:
        yield
    except Exception:
        _, _, tb = sys.exc_info()
        # formatted_tb = ''.join(
        #     traceback.format_list(traceback.extract_tb(tb)[1:]),
        # )
        _, _, fn, _ = traceback.extract_tb(tb, 2)[1]
        print(
            "\n{}\nFAIL: {} ({})\n{}".format(
                "=" * 80,
                fn,
                ", ".join("{0}={1!r}".format(k, v) for k, v in params.items()),
                "-" * 80,
            ),
            end="",
        )
        raise
