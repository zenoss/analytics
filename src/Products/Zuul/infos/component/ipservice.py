##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IIpServiceInfo
from Products.Zuul.infos.component import ComponentInfo, ServiceMonitor
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.decorators import info


class IpServiceInfo(ComponentInfo):
    implements(IIpServiceInfo)

    def __init__(self, *args, **kwargs):
        super(ComponentInfo, self).__init__(*args, **kwargs)
        if self._object.serviceclass() is not None:
            self.serviceClassUid = self._object.serviceclass().getPrimaryUrlPath()
        else:
            self.serviceClassUid = ""

    @property
    def name(self):
        return self._object.getKeyword()

    @property
    def usesMonitorAttribute(self):
        return not self._object.cantMonitor()

    @property
    def monitored(self):
        return self._object.monitored() if self.usesMonitorAttribute else ""

    monitor = ServiceMonitor()

    @property
    @info
    def serviceClass(self):
        return self._object.serviceclass()

    def getManageIp(self):
        return self._object.getManageIp()
    def setManageIp(self, value):
        self._object.manageIp = value
    manageIp = property(getManageIp, setManageIp)

    port = ProxyProperty('port')
    ipaddresses = ProxyProperty('ipaddresses')
    protocol = ProxyProperty('protocol')
    discoveryAgent = ProxyProperty('discoveryAgent')

    def getFailSeverity(self):
        return self._object.getFailSeverity()
    def setFailSeverity(self, value):
        if value is not None:
            self._object.zFailSeverity = value
        else:
            self._object.deleteZenProperty('zFailSeverity')
    failSeverity = property(getFailSeverity, setFailSeverity)

    def getSendString(self):
        return self._object.getSendString()
    def setSendString(self, value):
        self._object.setAqProperty("sendString", value, "string")
    sendString = property(getSendString, setSendString)

    def getExpectRegex(self):
        return self._object.getExpectRegex()
    def setExpectRegex(self, value):
        self._object.setAqProperty("expectRegex", value, "string")
    expectRegex = property(getExpectRegex, setExpectRegex)
