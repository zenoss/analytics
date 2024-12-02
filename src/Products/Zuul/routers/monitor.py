##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from Products import Zuul
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.interfaces import IInfo, ITreeNode
from Products.Zuul.routers import TreeRouter
from Products.ZenUtils.controlplane.client import ControlCenterError


log = logging.getLogger('zen.MonitorRouter')


class MonitorRouter(TreeRouter):
    """
    """

    def _getFacade(self):
        return Zuul.getFacade('monitors', self.context)

    def getTree(self, id):
        """
        Returns the tree structure of the application (service) hierarchy where
        the root node is the organizer identified by the id parameter.

        @type  id: string
        @param id: Id of the root node of the tree to be returned
        @rtype:   [dictionary]
        @return:  Object representing the tree
        """
        facade = self._getFacade()
        monitors = facade.query()
        nodes = map(ITreeNode, monitors)
        data = Zuul.marshal(nodes)
        return data

    def getInfo(self, id):
        """
        Returns the serialized info object for the given id
        @type: id: String
        @param id: Valid id of a application
        @rtype: DirectResponse
        @return: DirectResponse with data of the application
        """
        facade = self._getFacade()
        monitor = facade.get(id)
        data = Zuul.marshal(ITreeNode(monitor))
        return DirectResponse.succeed(data=data)

    def addCollector(self, id, sourceId, hubId, poolId):
        """
        Adds a collector to the hub specified by hub id.
        @type: id: String
        @param id: Valid id of a hub
        @rtype: DirectResponse
        @return: DirectResponse Upon success
        """
        facade = self._getFacade()
        try:
            monitor = IInfo(facade.addMonitor(
                id, sourceId=sourceId, hubId=hubId, poolId=poolId
            ))
        except ControlCenterError as e:
            log.error("Control Center error: %s", e.message)
            return DirectResponse.fail(e.message)
        return DirectResponse.succeed(data=Zuul.marshal(monitor))

    def getCollectors(self, query=None):
        facade = self._getFacade()
        collectors = [IInfo(collector) for collector in facade.query()]
        return DirectResponse.succeed(data=Zuul.marshal(collectors))

    def getCollector(self, collectorString):
        """
        Get a collector by name
        @type  collectorString: string
        @param collectorString: name of collector to return
        """
        facade = Zuul.getFacade('monitors', self.context)
        collector = IInfo(facade.get(collectorString))
        return DirectResponse.succeed(data=Zuul.marshal(collector))

