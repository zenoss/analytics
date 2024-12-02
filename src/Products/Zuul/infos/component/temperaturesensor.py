##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import ITemperatureSensorInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class TemperatureSensorInfo(ComponentInfo):
    implements(ITemperatureSensorInfo)

    state = ProxyProperty('state')

    @property
    def temperature(self):
        return self._object.temperatureFahrenheit()
