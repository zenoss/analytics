##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import implements
from Products.Zuul.interfaces import IOrganizerInfo, ILocationOrganizerInfo
from Products.Zuul.infos import InfoBase, HasEventsInfoMixin


class OrganizerInfo(InfoBase):
    implements(IOrganizerInfo)

    def setName(self, name):
        raise NotImplementedError('Can not set organizer name.')

    def _getDescription(self):
        return self._object.description

    def _setDescription(self, value):
        self._object.description = value

    description = property(_getDescription, _setDescription)

class DeviceClassInfo(OrganizerInfo, HasEventsInfoMixin):

    @property
    def connectionInfo(self):
        return self._object.getZ('zCredentialsZProperties')

    @connectionInfo.setter
    def connectionInfo(self, val):
        if isinstance(val, basestring):
            val = val.split("\n")
        self._object.setZenProperty('zCredentialsZProperties', val)
        
class LocationOrganizerInfo(OrganizerInfo, HasEventsInfoMixin):
    implements(ILocationOrganizerInfo)

    def getName(self):
        return self._object.getOrganizerName()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    def _getAddress(self):
        return self._object.address

    def _setAddress(self, value):
        # whenever the address changes invalidate the cached location
        self._object.address = value
        self._object.latlong = None

    address = property(_getAddress, _setAddress)
