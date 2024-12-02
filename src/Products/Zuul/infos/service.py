##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces import IServiceInfo, IIpServiceClassInfo
from Products.Zuul.interfaces import IServiceOrganizerNode, IWinServiceClassInfo
from Products.Zuul.interfaces import IServiceOrganizerInfo
from Products.ZenModel.IpServiceClass import IpServiceClass
from Products.ZenModel.WinServiceClass import WinServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.utils import catalogAwareImap


class ServiceOrganizerNode(TreeNode):
    implements(IServiceOrganizerNode)
    adapts(ServiceOrganizer)

    @property
    def iconCls(self):
        return ''

    @property
    def text(self):
        text = super(ServiceOrganizerNode, self).text
        obj = self._object.getObject()
        count = obj.countClasses()
        return {'text': text, 'count': count}

    @property
    def children(self):
        orgs = self._object.getObject().children()
        orgs.sort(key=lambda x: x.titleOrId())
        return catalogAwareImap(lambda x:ServiceOrganizerNode(x, self._root, self), orgs)

    @property
    def leaf(self):
        return False

class ServiceInfoBase(InfoBase):
     def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)
     def getZFailSeverity(self):
        def translate(rawValue):
            return {5: 'Critical',
                    4: 'Error',
                    3: 'Warning',
                    2: 'Info',
                    1: 'Debug'}[rawValue]
        return getZPropertyInfo(self._object, 'zFailSeverity', 4, translate)

     def setZFailSeverity(self, data):
        setZPropertyInfo(self._object, 'zFailSeverity', **data)

     zFailSeverity = property(getZFailSeverity, setZFailSeverity)


class ServiceInfo(ServiceInfoBase):
    implements(IServiceInfo)

    def setZMonitor(self, data):
        oldZMonitor = self._object.zMonitor
        setZPropertyInfo(self._object, 'zMonitor', **data)
        if self._object.zMonitor != oldZMonitor:
            self._object._indexInstances()

    zMonitor = property(ServiceInfoBase.getZMonitor, setZMonitor)

    def getServiceKeys(self):
        return self._object.serviceKeys

    def setServiceKeys(self, value):
        self._object.serviceKeys = value
        self._object.index_object()

    serviceKeys = property(getServiceKeys, setServiceKeys)

    def getName(self):
        return self._object.titleOrId()

    def setName(self, name):
        self._object.setTitle(name)
        self._object.name = name

    name = property(getName, setName)

    @property
    def count(self):
        return self._object.count()

class IpServiceClassInfo(ServiceInfo):
    adapts(IpServiceClass)
    implements(IIpServiceClassInfo)

    def getPort(self):
        return self._object.port

    def setPort(self, value):
        self._object.port = value

    port = property(getPort, setPort)

    def getSendString(self):
        return self._object.sendString

    def setSendString(self, value):
        self._object.sendString = value

    sendString = property(getSendString, setSendString)

    def getExpectRegex(self):
        return self._object.expectRegex

    def setExpectRegex(self, value):
        self._object.expectRegex = value

    expectRegex = property(getExpectRegex, setExpectRegex)


class WinServiceClassInfo(ServiceInfo):
    adapts(WinServiceClass)
    implements(IWinServiceClassInfo)

    def getMonitoredStartModes(self):
        return self._object.monitoredStartModes

    def setMonitoredStartModes(self, value):
        self._object.monitoredStartModes = value

    monitoredStartModes = property(getMonitoredStartModes, setMonitoredStartModes)

class ServiceOrganizerInfo(ServiceInfoBase):
    implements(IServiceOrganizerInfo)
    adapts(ServiceOrganizer)

    def setZMonitor(self, data):
        oldZMonitor = self._object.zMonitor
        setZPropertyInfo(self._object, 'zMonitor', **data)
        if self._object.zMonitor != oldZMonitor:
            self._object._indexServiceClassInstances()

    zMonitor = property(ServiceInfoBase.getZMonitor, setZMonitor)
