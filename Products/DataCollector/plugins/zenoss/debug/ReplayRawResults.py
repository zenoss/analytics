##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ReplayRawResults

Replay captured data which is  modeler plugin input, where the filename
are specified via the configuration file
($ZENHOME/etc/ReplayRawResults.conf)

File format
==============

[section1]
modeler_plugin = zenoss.snmp.InterfaceMap
raw_data_file = path/to/file

Notes
=======
* The section names are ignored
* The raw data files may be gzip'd
"""

import gzip
import logging
import pickle

from ConfigParser import RawConfigParser
from importlib import import_module

from Products.DataCollector.Plugins import loadPlugins
from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.zenmodeler.ReplayRawResults")


class MissingModelerPluginSectionArgument(Exception):
    pass


class ReplayRawResults(PythonPlugin):
    configFile = zenPath("etc/ReplayRawResults.conf")
    pluginPath = None

    def copyDataToProxy(self, dev, proxy):
        # Note: a 'super()' call explodes on subsequent runs of the plugin
        PythonPlugin.copyDataToProxy(self, dev, proxy)

        settings = self.getSettings()
        proxy.all_plugins = {}

        pluginPath = self.makePluginRegistry(dev.dmd)
        for section in settings.sections():
            modeler_plugin_name = settings.get(section, "modeler_plugin")
            data = pluginPath.get(modeler_plugin_name)
            if data:
                path, plugin = data
                plugin.copyDataToProxy(dev, proxy)
                proxy.all_plugins[modeler_plugin_name] = path
            else:
                log.error(
                    "Section %s modeler plugin '%s' not known",
                    section,
                    modeler_plugin_name,
                )

    def makePluginRegistry(self, dmd):
        pluginPath = {}
        for loader in loadPlugins(dmd):
            try:
                plugin = loader.create()
                plugin.loader = loader
                # Note: can't return the actual plugin code because
                #       zenhubworkers will puke with an import error
                #       while unpickling the data.
                # ERROR zen.ZenHub: Error un-pickling result from worker
                path = loader.modPath
                if not path.startswith("ZenPack"):
                    path = "Products.DataCollector.plugins." + path
                pluginPath[plugin.name()] = (path, plugin)
            except Exception:
                log.exception("Unable to load plugin '%s'", loader)
        return pluginPath

    def collect(self, device, log):
        return self.getSettings()

    def getSettings(self):
        settings = RawConfigParser()
        settings.read(self.configFile)
        return settings

    def process(self, proxy, settings, log):
        log.info(
            "Modeler %s processing data for device %s", self.name(), proxy.id
        )
        self.log = log
        mapList = []
        for section in settings.sections():
            modeler_plugin_name = settings.get(section, "modeler_plugin")
            plugin = self.getPlugin(proxy, modeler_plugin_name)
            if plugin is None:
                continue

            results = self.readRawResults(settings, section)
            if results:
                try:
                    preppedResults = plugin.preprocess(results, log)
                    maps = plugin.process(proxy, preppedResults, log)
                    if isinstance(maps, list):
                        mapList.extend(maps)
                    else:
                        mapList.append(maps)
                except Exception:
                    log.exception(
                        "Unable to process raw data with plugin %s",
                        modeler_plugin_name,
                    )
        return mapList

    def readRawResults(self, settings, section):
        filename = settings.get(section, "raw_data_file")
        results = []
        try:
            results = self.readRawDataFile(filename)
        except Exception as ex:
            self.log.warn(
                "Unable to read processed data file '%s': %s", filename, ex
            )

        if not results:
            self.log.warn("No data in file '%s'", filename)

        return results

    def readRawDataFile(self, filename):
        opener = open
        if filename.endswith(".gz"):
            opener = gzip.open

        with opener(filename) as fd:
            result = pickle.load(fd)
            return result

    def getPlugin(self, proxy, modeler_plugin_name):
        """
        This gets called in the zenmodeler daemon on the remote collector.
        """
        pluginPath = proxy.all_plugins.get(modeler_plugin_name)
        if pluginPath is None:
            log.error(
                "Unable to locate the modeler plugin '%s'", modeler_plugin_name
            )
            return

        try:
            module = import_module(pluginPath)
            # Convention is that the class representing the modeler
            # plugin be named the same as the file it lives in
            name = modeler_plugin_name.rsplit(".", 1)[1]
            klass = getattr(module, name, None)
            if klass is None:
                log.error(
                    "The class '%s' is not found in the module %s",
                    name,
                    modeler_plugin_name,
                )
                return
        except Exception:
            log.exception("Unable to import %s", modeler_plugin_name)
            return

        plugin = None
        try:
            plugin = klass()
        except Exception:
            log.exception("Unable to import %s", modeler_plugin_name)

        return plugin
