##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IExpansionCardInfo
from Products.Zuul.decorators import info
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class ExpansionCardInfo(ComponentInfo):
    implements(IExpansionCardInfo)

    slot = ProxyProperty('slot')
    serialNumber = ProxyProperty('serialNumber')
    socket = ProxyProperty('socket')
    clockspeed = ProxyProperty('clockspeed')
    extspeed = ProxyProperty('extspeed')
    voltage = ProxyProperty('voltage')
    cacheSizeL1 = ProxyProperty('cacheSizeL1')
    cacheSizeL2 = ProxyProperty('cacheSizeL2')

    @property
    @info
    def manufacturer(self):
        pc = self._object.productClass()
        if (pc):
            return pc.manufacturer()

    @property
    @info
    def product(self):
        return self._object.productClass()

    @property
    def usesMonitorAttribute(self):
        return False

    monitor = False

    @property
    def monitored(self):
        return ""
