##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IIpRouteEntryInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo

class IpRouteEntryInfo(ComponentInfo):
    implements(IIpRouteEntryInfo)

    @property
    @info
    def destination(self):
        target = self._object.target()
        return target if target else self._object._target

    @property
    @info
    def nextHop(self):
        ip = self._object.nexthop()
        return ip if ip else self._object._nexthop

    @property
    @info
    def interface(self):
        return self._object.interface()

    @property
    def usesMonitorAttribute(self):
        return False

    monitor = False

    @property
    def monitored(self):
        return ""

    protocol = ProxyProperty('routeproto')
    type = ProxyProperty('routetype')
