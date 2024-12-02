##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IWinServiceInfo
from Products.Zuul.infos.component import ComponentInfo, ServiceMonitor
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.decorators import info
from Products.Zuul.utils import safe_hasattr

class WinServiceInfo(ComponentInfo):
    implements(IWinServiceInfo)

    def __init__(self, *args, **kwargs):
        super(ComponentInfo, self).__init__(*args, **kwargs)
        if self._object.serviceclass() is not None:
            self.serviceClassUid = self._object.serviceclass().getPrimaryUrlPath()
        else:
            self.serviceClassUid = ""

    @property
    @info
    def serviceClass(self):
        return self._object.serviceclass()

    @property
    def monitored(self):
        return self._object.monitored() if self.usesMonitorAttribute else ""

    monitor = ServiceMonitor()

    @property
    def caption(self):
        return self._object.caption()

    command = ProxyProperty('id')

    def getFailSeverity(self):
        return self._object.getFailSeverity()
    def setFailSeverity(self, value):
        if value is not None:
            self._object.zFailSeverity = value
        else:
            self._object.deleteZenProperty('zFailSeverity')
    failSeverity = property(getFailSeverity, setFailSeverity)

    @property
    def status(self):
        status = self._object.getStatus()
        if status < 0: return 'none'
        elif status == 0: return 'up'
        else: return 'down'

    serviceName = ProxyProperty('serviceName')
    caption = ProxyProperty('caption')
    serviceType = ProxyProperty('serviceType')
    startMode = ProxyProperty('startMode')
    startName = ProxyProperty('startName')
    pathName = ProxyProperty('pathName')
