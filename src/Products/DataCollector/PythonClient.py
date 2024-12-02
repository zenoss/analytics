##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.internet.defer import Deferred, DeferredList
from twisted.python.failure import Failure

from .BaseClient import BaseClient

log = logging.getLogger("zen.PythonClient")


class PythonClient(BaseClient):
    """
    Python performance data collector client.
    """

    def __init__(self, device=None, datacollector=None, plugins=[]):
        """
        Initializer

        @param device: remote device to use the datacollector
        @type device: device object
        @param datacollector: performance data collector object
        @type datacollector: datacollector object
        @param plugins: Python-based performance data collector plugin
        @type plugins: list of plugin objects
        """
        BaseClient.__init__(self, device, datacollector)
        self.hostname = device.id
        self.plugins = plugins
        self.results = []

    def run(self):
        """
        Start Python collection.
        """
        deferreds = []
        for plugin in self.plugins:
            log.debug("Running collection for plugin %s", plugin.name())
            r = plugin.collect(self.device, log)
            if isinstance(r, Deferred):
                deferreds.append(r)
                r.addBoth(self.collectComplete, plugin)
            else:
                log.debug("Results for %s: %s", plugin.name(), str(r))
                self.results.append((plugin, r))

        dl = DeferredList(deferreds)
        dl.addCallback(self.collectComplete, None)

    def collectComplete(self, r, plugin):
        """
        Twisted deferred error callback used to store the
        results of the collection run

        @param r: result from the collection run
        @type r: result or Exception
        @param plugin: Python-based performance data collector plugin
        @type plugin: plugin object
        """
        if plugin is None:
            self.clientFinished()
            return

        if isinstance(r, Failure):
            log.error("Error in %s: %s", plugin.name(), r.getErrorMessage())
        else:
            log.debug("Results for %s: %s", plugin.name(), str(r))
            self.results.append((plugin, r))

    def clientFinished(self):
        """
        Stop the collection of performance data
        """
        log.info("Python client finished collection for %s", self.device.id)
        if self.datacollector:
            self.datacollector.clientFinished(self)

    def getResults(self):
        """
        Return the results of the data collection.
        To be implemented by child classes

        @return: list of results
        @rtype: list of results
        """
        return self.results
