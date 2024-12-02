##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Load modeling and monitoring plugins from standard locations and from
ZenPacks.  Most of the entry into this module is via the three functions
defined at the very bottom of the file. Those functions use the singleton
PluginManager objects to load the plugins.

Classes -
    PluginImportError - an exception type
    PluginLoader - jellyable object that has all the information neccessary
                   to dynamically import the plugin module and instantiate the
                   class that shares the module's name
    CoreImporter - jellyable object that is injected into a PluginLoader.
                   handles importing of plugins found inside Products
    PackImporter - same as above but for zenpack plugins
    BaseLoaderFactory - base class for the two loader factories
    CoreLoaderFactory - generates the PluginLoaders for core plugins
    PackLoaderFactory - generates the PluginLoaders for zenpack plugins
    PluginManager - there is one singleton instance of this class for modeling
                    plugins and another for monitoring plugins

Note that modPath uses a different convention for core versus zenpack plugins.

    core: zenoss.cmd.uname
    zenpack: ZenPacks.zenoss.AixMonitor.modeler.plugins.zenoss.cmd.uname

"""

import exceptions
import imp
import logging
import os
import sys

from importlib_resources import files as getFilePathOf
from twisted.spread import pb

from Products.ZenUtils.Utils import importClass

log = logging.getLogger("zen.Plugins")


class PluginImportError(exceptions.ImportError):
    """
    Capture extra data from plugin exceptions
    """

    def __init__(self, plugin="", traceback=""):
        """
        Initializer

        @param plugin: plugin name
        @type plugin: string
        @param traceback: traceback from an exception
        @type traceback: traceback object
        """
        self.plugin = plugin
        self.traceback = traceback
        # The following is needed for zendisc
        self.args = traceback


class PluginLoader(pb.Copyable, pb.RemoteCopy):
    """
    Class to load plugins
    """

    def __init__(self, package, modPath, lastModName, importer):
        """
        package - '/'-separated absolute path to the root of the plugins
                  modules
        modPath - '.'-spearated module path.  for core plugins, it is rooted
                  at the package.  for zenpack plugins, it starts with
                  'ZenPacks'
        lastModName - name of the last module in modPath that is not part of
                  of the plugin name
        importer - object with an importPlugin method used to import the
                   plugin. the implementation of the import method differs
                   between core and zenpack plugins
        """
        self.package = package
        self.modPath = modPath
        self.pluginName = modPath.split(lastModName + ".")[-1]
        self.importer = importer

    def create(self):
        """
        Load and compile the code contained in the given plugin
        """
        try:
            try:
                # Modify sys.path (some plugins depend on this to import other
                # modules from the plugins root)
                sys.path.insert(0, self.package)
                pluginClass = self.importer.importPlugin(
                    self.package, self.modPath
                )
                return pluginClass()
            except Exception:
                import traceback

                log.debug(traceback.format_exc())
                raise PluginImportError(
                    plugin=self.modPath,
                    traceback=traceback.format_exc().splitlines(),
                )
        finally:
            try:
                sys.path.remove(self.package)
            except ValueError:
                # It's already been removed
                pass


pb.setUnjellyableForClass(PluginLoader, PluginLoader)


def _coreModPaths(walker, package):
    "generates modPath strings for the modules in a core directory"
    for absolutePath, _, filenames in walker.walk(package):
        if absolutePath == package:
            modPathBase = []
        elif absolutePath.startswith(package):
            modPathBase = absolutePath[len(package) + 1 :].split(os.path.sep)
        else:
            log.debug(
                "absolutePath must start with package: "
                "absolutePath=%s, package=%s",
                absolutePath,
                package,
            )
            continue
        for filename in filenames:
            if (
                filename.endswith(".py")
                and filename[0] not in (".", "_")
                and "#" not in filename
                and filename not in ("CollectorPlugin.py", "DataMaps.py")
            ):
                yield ".".join(modPathBase + [filename[:-3]])


class OsWalker(object):
    def walk(self, package):
        return os.walk(package)


class CoreImporter(pb.Copyable, pb.RemoteCopy):
    def importModule(self, package, modPath):
        fp = None
        # Load the plugins package using its path as the name to
        # avoid conflicts. slashes in the name are OK when using
        # the imp module.
        parts = modPath.split(".")
        path = package
        try:
            for partNo in range(1, len(parts) + 1):
                part = parts[partNo - 1]
                fp, path, description = imp.find_module(part, [path])
                modSubPath = ".".join(parts[:partNo])
                mod = imp.load_module(modSubPath, fp, path, description)
        finally:
            if fp:
                fp.close()
        return mod

    def importPlugin(self, package, modPath):
        parts = modPath.split(".")
        # class name is same as module name
        clsname = parts[-1]
        mod = self.importModule(package, modPath)
        return getattr(mod, clsname)


pb.setUnjellyableForClass(CoreImporter, CoreImporter)


class PackImporter(pb.Copyable, pb.RemoteCopy):
    def importModule(self, package, modPath):
        modulePath = modPath
        try:
            classname = modulePath.split(".")[-1]
            try:
                __import__(modulePath, globals(), locals(), classname)
                mod = sys.modules[modulePath]
            except (ValueError, ImportError, KeyError) as ex:
                raise ex

            return mod
        except AttributeError:
            raise ImportError(
                "Failed while importing module %s" % (modulePath)
            )

    def importPlugin(self, package, modPath):
        # ZenPack plugins are specified absolutely; we can import
        # them using the old method
        return importClass(modPath)


pb.setUnjellyableForClass(PackImporter, PackImporter)


class BaseLoaderFactory(object):
    def __init__(self, walker):
        self.walker = walker

    def genLoaders(self, package, lastModName):
        for coreModPath in _coreModPaths(self.walker, package):
            yield self._createLoader(package, coreModPath, lastModName)


class CoreLoaderFactory(BaseLoaderFactory):
    def _createLoader(self, package, coreModPath, lastModName):
        return PluginLoader(package, coreModPath, lastModName, CoreImporter())


class PackLoaderFactory(BaseLoaderFactory):
    def __init__(self, walker, modPathPrefix):
        BaseLoaderFactory.__init__(self, walker)
        self.modPathPrefix = modPathPrefix

    def _createLoader(self, package, coreModPath, lastModName):
        packModPath = "%s.%s" % (self.modPathPrefix, coreModPath)
        return PluginLoader(package, packModPath, lastModName, PackImporter())


class PluginManager(object):
    """
    Manages plugin modules.  Finds plugins and returns PluginLoader instances.
    Keeps a cache of previously loaded plugins.
    """

    def __init__(self, lastModName, packPath, productsPaths):
        """
        Adds PluginLoaders for plugins in productsPaths to the pluginLoaders
        dictionary.

        lastModName - The directory name where the plugins are found.
            This name is appended to the following paths
        packPath - Path to the directory that holds the plugin modules inside
            a zenpack. This path is relative to the zenpack root
        productsPaths - List of paths to directories that hold plugin
            modules. These paths are relative to $ZENHOME/Products

        a 'path', as used here, is a tuple of directory names
        """
        self.pluginLoaders = {}  # PluginLoaders by module path
        self.loadedZenpacks = []  # zenpacks that have been processed
        self.lastModName = lastModName
        self.packPath = packPath
        for path in productsPaths:
            package = getFilePathOf(
                "Products.{}.{}".format(path, lastModName)
            ).as_posix()
            self._addPluginLoaders(CoreLoaderFactory(OsWalker()), package)

    def getPluginLoader(self, packs, modPath):
        """
        Get the PluginLoader for a specific plugin.

        packs - list of installed zenpacks (ZenPack instances)
        modPath - the module path of the plugin
        """
        if not modPath:
            return None
        if modPath not in self.pluginLoaders:
            self.getPluginLoaders(packs)
        if modPath in self.pluginLoaders:
            return self.pluginLoaders[modPath]

    def getPluginLoaders(self, packs):
        """
        Add the PluginLoaders for the packs to the pluginLoaders dictionary.
        Return the values of that dictionary.

        packs - list of installed zenpacks (ZenPack instances)
        """
        try:
            for pack in packs:
                modname = pack.moduleName()
                if modname not in self.loadedZenpacks:
                    self.loadedZenpacks.append(modname)
                    modPathPrefix = ".".join(
                        (modname,) + self.packPath + (self.lastModName,)
                    )
                    factory = PackLoaderFactory(OsWalker(), modPathPrefix)
                    package = pack.path(*self.packPath + (self.lastModName,))
                    self._addPluginLoaders(factory, package)
        except Exception:
            log.error(
                "Could not load plugins from ZenPacks."
                " One of the ZenPacks is missing or broken."
            )
            import traceback

            log.debug(traceback.format_exc())
        return self.pluginLoaders.values()

    def _addPluginLoaders(self, loaderFactory, package):
        log.debug("Loading collector plugins from: %s", package)
        try:
            loaders = loaderFactory.genLoaders(package, self.lastModName)
            for loader in loaders:
                self.pluginLoaders[loader.modPath] = loader
        except Exception:
            log.error("Could not load plugins from %s", package)
            import traceback

            log.debug(traceback.format_exc())


class ModelingManager(object):
    """
    this class is not intended to be instantiated. instead it is a place to
    hold a singleton instance of PluginManager without having them call the
    constructor when this module is imported.
    """

    instance = None

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = PluginManager(
                lastModName="plugins",
                packPath=("modeler",),
                productsPaths=("DataCollector",),
            )
        return cls.instance


class MonitoringManager(object):
    """
    this class is not intended to be instantiated. instead it is a place to
    hold a singleton instance of PluginManager without having them call the
    constructor when this module is imported.
    """

    instance = None

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = PluginManager(
                lastModName="parsers", packPath=(), productsPaths=("ZenRRD",)
            )
        return cls.instance


def _loadPlugins(pluginManager, dmd):
    return pluginManager.getPluginLoaders(dmd.ZenPackManager.packs())


def loadPlugins(dmd):
    "Get PluginLoaders for all the modeling plugins"
    return _loadPlugins(ModelingManager.getInstance(), dmd)


def loadParserPlugins(dmd):
    "Get PluginLoaders for all the modeling plugins"
    return _loadPlugins(MonitoringManager.getInstance(), dmd)


def getParserLoader(dmd, modPath):
    "Get a PluginLoader for the given monitoring plugin's module path"
    return MonitoringManager.getInstance().getPluginLoader(
        dmd.ZenPackManager.packs(), modPath
    )
