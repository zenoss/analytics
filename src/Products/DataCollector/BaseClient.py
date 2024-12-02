##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


class BaseClient(object):
    """
    Base client class for the data collection.
    """

    def __init__(self, device, datacollector):
        """
        Initializer

        @param device: remote device to use the datacollector
        @type device: device object
        @param datacollector: performance data collector object
        @type datacollector: datacollector object
        """
        self.hostname = None
        if device:
            self.hostname = device.id
        self.device = device
        self.datacollector = datacollector
        self.timeout = None
        self.timedOut = False

    def run(self):
        """
        Start the data gathering.
        To be implemented by child classes
        """

    def stop(self):
        """
        Stopping condition for the collector.
        To be implemented by child classes
        """

    def getResults(self):
        """
        Return the results of the data collection.
        To be implemented by child classes

        @return: list of results
        @rtype: list of results
        """
        return []
