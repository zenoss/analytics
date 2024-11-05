##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""ReplayProcessedResults

Replay captured and processed modeler plugin output, where the filenames
are specified via comma-separated entries in the configuration file
($ZENHOME/etc/ReplayProcessedResults.conf)

File format
==============

[section1]
processed_files = path/to/file

Notes
=======
* The section names are ignored
* The processesd files may be gzip'd
"""

import gzip
import pickle

from ConfigParser import RawConfigParser

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.ZenUtils.path import zenPath


class ReplayProcessedResults(PythonPlugin):
    configFile = zenPath("etc/ReplayProcessedResults.conf")

    def collect(self, device, log):
        settings = RawConfigParser()
        settings.read(self.configFile)
        return settings

    def process(self, device, settings, log):
        log.info(
            "Modeler %s processing data for device %s", self.name(), device.id
        )
        self.log = log
        mapList = []
        for section in settings.sections():
            maps = self.readRelMaps(settings, section)
            if maps:
                mapList.extend(maps)
        return mapList

    def readRelMaps(self, settings, section):
        filenameList = settings.get(section, "processed_files")
        mapList = []
        for filename in filenameList.split(","):
            filename = filename.strip()
            try:
                maps = self.readRelMap(filename)
            except Exception as ex:
                self.log.warn(
                    "Unable to read processed data file '%s': %s", filename, ex
                )
                continue

            if not maps:
                self.log.warn("No data in file '%s'", filename)
            elif isinstance(maps, list):
                mapList.extend(maps)
            else:
                mapList.append(maps)

        return mapList

    def readRelMap(self, filename):
        opener = open
        if filename.endswith(".gz"):
            opener = gzip.open

        with opener(filename) as fd:
            result = pickle.load(fd)
            return result
