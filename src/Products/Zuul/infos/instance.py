##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from zope.component import adapts
from Products.Zuul.interfaces import IInstanceInfo, IInstance
from Products.Zuul.infos import InfoBase

class ComponentInfo(InfoBase):
    implements(IInstanceInfo)
    adapts(IInstance)

    def __init__(self, obj):
        self._object = obj

    @property
    def id(self):
        '.'.join(self._object.getPrimaryPath())

    @property
    def device(self):
        return self._object.device().titleOrId()

    @property
    def name(self):
        return self._object.name()

    @property
    def monitored(self):
        return self._object.zMonitor

    @property
    def status(self):
        statusCode = self._object.getStatus()
        return self._object.convertStatus(statusCode)
