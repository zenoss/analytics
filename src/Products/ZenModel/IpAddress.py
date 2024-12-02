##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """IpAddress

IpAddress represents a device residing on an IP network.
"""

import socket
import logging
log = logging.getLogger("zen.IpAddress")

#base classes for IpAddress
from ManagedEntity import ManagedEntity

from ipaddr import IPAddress

from AccessControl import ClassSecurityInfo
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
import zope.interface
from Products import Zuul
from Products.Zuul.interfaces import IInfo
from Products.ZenUtils.jsonutils import json
from Products.Zuul.utils import allowedRolesAndUsers
from Products.ZenRelations.RelSchema import ToOne, ToMany, ToManyCont
from Products.ZenUtils.IpUtil import maskToBits, checkip, ipToDecimal, netFromIpAndNet, \
                                     ipwrap, ipunwrap, ipunwrap_strip
from Products.ZenModel.Exceptions import WrongSubnetError
from Products.ZenUtils.IpUtil import numbip
from Products.Zuul.catalog.indexable import IpAddressIndexable

def manage_addIpAddress(context, id, netmask=24, REQUEST = None):
    """make an IpAddress"""
    ip = IpAddress(id, netmask)
    context._setObject(ip.id, ip)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main')


addIpAddress = DTMLFile('dtml/addIpAddress',globals())


class IpAddress(ManagedEntity, IpAddressIndexable):
    """IpAddress object"""

    event_key = portal_type = meta_type = 'IpAddress'

    default_catalog = 'ipSearch'

    version = 4

    _properties = (
        {'id':'netmask', 'type':'string', 'mode':'w', 'setter':'setNetmask'},
        {'id':'ptrName', 'type':'string', 'mode':'w'},
        {'id':'version', 'type':'int', 'mode':'w'},
        )
    _relations = ManagedEntity._relations + (
        ("network", ToOne(ToManyCont,"Products.ZenModel.IpNetwork","ipaddresses")),
        ("interface", ToOne(ToMany,"Products.ZenModel.IpInterface","ipaddresses")),
        ("manageDevice", ToOne(ToOne,"Products.ZenModel.Device","ipaddress")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","nexthop")),
        )

    factory_type_information = (
        {
            'id'             : 'IpAddress',
            'meta_type'      : 'IpAddress',
            'description'    : """Ip Address Class""",
            'icon'           : 'IpAddress_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpAddress',
            'immediate_view' : 'viewIpAddressOverview',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewIpAddressOverview'
                , 'permissions'   : ( "View", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, netmask=24):
        checkip(id)
        ManagedEntity.__init__(self, ipwrap(id))
        ipobj = IPAddress(ipunwrap_strip(id))
        if ipobj.version == 6:
            # No user-definable subnet masks for IPv6
            netmask = 64
        self._netmask = maskToBits(netmask)
        self.ptrName = None
        self.title = ipunwrap(id)
        self.version = ipobj.version

    def _pre_remove(self):
        self.manageDevice.removeRelation()
        self.interface.removeRelation()
        self.clientroutes.removeRelation()

    def setPtrName(self):
        try:
            data = socket.gethostbyaddr(ipunwrap(self.id))
            if data: self.ptrName = data[0]
        except socket.error as e:
            self.ptrName = ""
            log.warn("%s: %s", self.title, e)

    security.declareProtected('View', 'primarySortKey')
    def primarySortKey(self):
        """
        Make sure that networks sort correctly
        """
        return ipToDecimal(self.id)

    def setNetmask(self, value):
        self._netmask = maskToBits(value)

    def _setPropValue(self, id, value):
        """
        Override from PerpertyManager to handle checks and IP creation
        """
        self._wrapperCheck(value)
        if id == 'netmask':
            self.setNetmask(value)
        else:
            setattr(self,id,value)

    def __getattr__(self, name):
        if name == 'netmask':
            return self._netmask
        else:
            raise AttributeError( name )

    security.declareProtected('Change Device', 'setIpAddress')
    def setIpAddress(self, ip):
        """
        Set the IP address. Use the format 1.1.1.1/24 to also set the netmask
        """
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            self._netmask = maskToBits(iparray[1])
        checkip(ip)
        aqself = self.primaryAq() #set aq path
        network = aqself.aq_parent
        netip = netFromIpAndNet(ip, network.netmask)
        if netip == network.id:
            network._renameObject(aqself.id, ipwrap(ip))
        else:
            raise WrongSubnetError(
                    "IP %s is in a different subnet than %s" % (ipunwrap(ip), ipunwrap(self.id)) )

    security.declareProtected('View', 'getIp')
    def getIp(self):
        """
        Return only the IP address
        """
        return ipunwrap(self.id)

    security.declareProtected('View', 'getIpAddress')
    def getIpAddress(self):
        """
        Return the IP with its netmask in the form 1.1.1.1/24
        """
        return ipunwrap(self.id) + "/" + str(self._netmask)

    def __str__(self):
        return self.getIpAddress()

    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        if self.interface():
            return self.interface().name()
        return "No Interface"

    security.declareProtected('View', 'getDeviceName')
    def getDeviceName(self):
        if self.interface():
            return self.device().titleOrId()
        return "No Device"

    security.declareProtected('View', 'getNetworkName')
    def getNetworkName(self):
        if self.network():
            return self.network().getNetworkName()
        return "No Network"

    def getInterfaceDescription(self):
        """
        Used for indexing
        """
        if self.interface():
            return self.interface().description

    def getInterfaceMacAddress(self):
        """
        Used for indexing
        """
        if self.interface():
            return self.interface().macaddress

    security.declareProtected('View', 'getNetworkUrl')
    def getNetworkUrl(self):
        if self.network():
            return self.network().absolute_url_path()
        return ""

    security.declareProtected('View', 'getDeviceUrl')
    def getDeviceUrl(self):
        """
        Get the primary URL path of the device to which this IP
        is associated.  If no device return the URL to the IP itself.
        """
        d = self.device()
        if d:
            return d.getPrimaryUrlPath()
        else:
            return self.getPrimaryUrlPath()

    def device(self):
        """
        Return the device for this IP
        """
        iface = self.interface()
        if iface: return iface.device()
        return None

    def index_object(self, idxs=None):
        """ DEPRECATED """
        pass

    def unindex_object(self):
        """ DEPRECATED """
        pass

    def deviceId(self):
        """
        The device id, for indexing purposes.
        """
        d = self.device()
        if d: return d.id
        else: return None

    def interfaceId(self):
        """
        The interface id, for indexing purposes.
        """
        i = self.interface()
        if i: return i.id
        else: return None

    def ipAddressId(self):
        """
        The ipAddress id, for indexing purposes.
        """
        return self.getPrimaryId()

    def networkId(self):
        """
        The network id, for indexing purposes.
        """
        n = self.network()
        if n: return n.getPrimaryId()
        else: return None

    def ipAddressAsInt(self):
        ip = self.getIpAddress()
        if ip:
            ip = ip.partition('/')[0]
        return str(numbip(ip))

    #------------------------------------------
    #--    ITreeSpanningComponent methods   --

    def get_indexable_peers(self):
        """  """
        peers = []
        if self.device():
            peers.append(self.device().primaryAq())
        if self.manageDevice():
            peers.append(self.manageDevice().primaryAq())
        if self.interface():
            peers.append(self.interface().primaryAq())
        return peers

InitializeClass(IpAddress)
