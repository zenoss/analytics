##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.interface import implements
from Products.Zuul.infos.component import ComponentInfo
from Products.Zuul.interfaces import IIpInterfaceInfo
from Products.Zuul.decorators import info
from Products.Zuul.infos import ProxyProperty

def ipAddressVocab(context):
    return context.ips

class IpInterfaceInfo(ComponentInfo):
    implements(IIpInterfaceInfo)

    def getIpAddresses(self):
        return ",".join([str(i) for i in self._object.getIpAddresses()])

    def setIpAddresses(self, ips):
        ips = ips.split(',')
        self._object.setIpAddresses(ips)
    ipAddresses = property(getIpAddresses, setIpAddresses)

    def _ipAddressObj(self):
        obj = self._object.getIpAddressObj()
        if obj is not None:
            return obj.primaryAq()

    @property
    @info
    def ipAddress(self):
        return self._ipAddressObj()

    @property
    @info
    def ipAddressObjs(self):
        return self._object.getIpAddressObjs()

    @property
    @info
    def network(self):
        ipAddr = self._ipAddressObj()
        if ipAddr:
            return ipAddr.network().primaryAq()

    interfaceName = ProxyProperty('interfaceName')
    ifindex = ProxyProperty('ifindex')
    macaddress = ProxyProperty('macaddress')
    type = ProxyProperty('type')
    mtu = ProxyProperty('mtu')

    @property
    def speed(self):
        return self._object.niceSpeed()

    @property
    def adminStatus(self):
        return self._object.getAdminStatusString()

    @property
    def operStatus(self):
        return self._object.getOperStatusString()

    @property
    def ifStatus(self):
        return {'adminStatus': self.adminStatus, 'operStatus': self.operStatus}

    @property
    @info
    def duplex(self):
        return self._object.niceDuplex()
