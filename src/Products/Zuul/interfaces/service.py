##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IFacade
from tree import ITreeNode
from info import IInfo

class IServiceFacade(IFacade):

    def getInfo(nodeId):
        """
        Get the Services tree by a serviceTreeNodeId.
        """

    def moveServices(sourceUids, targetUid):
        """
        Move ServiceOrganizers and ServiceClasses uniquely identified by the
        sourceUids parameter to the ServiceOrganizer uniquely identified by
        the targetUid parameter.
        """

class IServiceOrganizerNode(ITreeNode):
    """
    Marker interface for providing a Service node in a Service tree.
    """

class IServiceEntity(Interface):
    """
    Marker interface for ServiceClass and ServiceOrganizer
    """

class IServiceInfo(IInfo):
    """
    Represents a single ServiceClass instance.
    """
    name = Attribute('The name of the service')
    description = Attribute('A description of the service')
    serviceKeys = Attribute('Keys which will match for defining services.')
    count = Attribute('The number of instances.')
    zMonitor = Attribute('Is the service monitored')
    zFailSeverity = Attribute('The event severity for failure events')

class IIpServiceClassInfo(IServiceInfo):
    port = Attribute('The port that the service runs on')
    sendString = Attribute('A value sent to the port')
    expectRegex = Attribute('A regular expression matching the response to the send string')

class IWinServiceClassInfo(IServiceInfo):
    monitoredStartModes = Attribute('Start modes that will be monitored')

class IServiceOrganizerInfo(IInfo):
    """
    Represents a single ServiceOrganizer instance.
    """
    name = Attribute('The name of the service')
    description = Attribute('A description of the service')
