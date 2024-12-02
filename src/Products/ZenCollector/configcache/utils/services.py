##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import importlib
import inspect
import itertools
import pathlib2 as pathlib

import Products

from Products.ZenCollector.services.config import CollectorConfigService

_excluded_config_classes = (
    "NullConfigService",
    "NullConfig",
    "SnmpTrapConfig",
)


def mod_from_path(path):
    """
    Returns the module path of the given path to a Python code file.

    The module path is the path to a file with a ".py" extension.
    The package path is rooted at "Products" or "ZenPacks".

    >>> from pathlib2 import Path
    >>> mod_from_path(Path("/mnt/src/zenoss-prodbin/src/Products/ZenHub/services/ProcessConfig.py"))
    Products.ZenHub.services.ProcessConfig

    :param path: The module path
    :type path: pathlib.Path
    :returns: The package path
    :rtype: pathlib.Path
    """  # noqa: E501
    rpath = path.parts[::-1]  # reverse the path
    if "Products" in rpath:
        offset = rpath.index("Products")
    elif "ZenPacks" in rpath:
        offset = rpath.index("ZenPacks")
    return ".".join(itertools.chain(rpath[1 : offset + 1][::-1], [path.stem]))


def getConfigServicesFromModule(name):
    """
    Returns a tuple containing all the config service classes in the module.
    An empty tuple is returned if no config service classes are found.

    :param name: The full name of the module.
    :type name: pathlib.Path
    :returns: Tuple of Configuration service classes
    :rtype: tuple[CollectorConfigService]
    """
    try:
        mod = importlib.import_module(name)
        classes = (
            cls
            for nm, cls in inspect.getmembers(mod, inspect.isclass)
            if cls.__module__ == mod.__name__
        )
        # CollectorConfigService is excluded because it is the base
        # class for all other configuration services and not used
        # directly by any collection daemon.
        return tuple(
            cls
            for cls in classes
            if cls is not CollectorConfigService
            and issubclass(cls, CollectorConfigService)
        )
    except ImportError:
        return ()


def getDeviceConfigServices():
    """
    Returns a tuple containing all the installed config service classes.
    An empty tuple is returned if no config service classes are found.

    Configuration service classes are expected to be found in modules
    that found in a package named "services".  The "services" package can
    be found in multiple package paths.

    :returns: Tuple of configuration service classes
    :rtype: tuple[CollectorConfigService]
    """
    # defer import ZenPacks until here because it doesn't exist during
    # an image build.
    import ZenPacks

    search_paths = (
        pathlib.Path(p)
        for p in itertools.chain(Products.__path__, ZenPacks.__path__)
    )
    service_paths = (
        svcpath
        for path in search_paths
        for svcpath in path.rglob("**/services")
    )
    module_names = (
        mod_from_path(codepath)
        for path in service_paths
        for codepath in path.rglob("*.py")
        if codepath.stem != "__init__" and "tests" not in codepath.parts
    )
    return tuple(
        cls
        for cls in itertools.chain.from_iterable(
            getConfigServicesFromModule(name) for name in module_names
        )
        if cls.__name__ not in _excluded_config_classes
    )
