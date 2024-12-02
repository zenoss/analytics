##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""RouteEntry

RouteEntry represents a group of devices
"""

import re

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenUtils.Utils import localIpCheck, prepId
from Products.ZenRelations.RelSchema import *

from Products.ZenModel.interfaces import IObjectEventsSubscriber
from zope.interface import implements

from OSComponent import OSComponent

import logging
log = logging.getLogger("zen.IpRouteEntry")

def manage_addIpRouteEntry(context, dest, routemask, nexthopid, interface, 
                   routeproto, routetype, userCreated=None, REQUEST = None):
    """
    Make a IpRouteEntry from the ZMI
    """
    if not routemask:
        routemask = 0
    else:
        routemask = int(routemask)
    dest = '%s/%s' % (dest, routemask)
    id = prepId(dest)
    d = IpRouteEntry(id)
    context._setObject(id, d)
    d = context._getOb(id)
    d.setTarget(dest)
    d.setNextHopIp(nexthopid)
    d.setInterfaceName(interface)
    if userCreated: d.setUserCreateFlag()
    d.routeproto = routeproto
    d.routetype = routetype
    d.routemask = routemask
    
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 

addIpRouteEntry = DTMLFile('dtml/addIpRouteEntry',globals())


class IpRouteEntry(OSComponent):
    """
    IpRouteEntry object
    """

    implements(IObjectEventsSubscriber)
    
    meta_type = 'IpRouteEntry'

    # we don't monitor routes
    monitor = False
    
    _nexthop = ""
    _target = ""
    _targetobj = None
    routetype = ""
    routeproto = ""
    routemask = 0
    routeage = 0
    metric1 = 0
    metric2 = 0
    metric3 = 0
    metric4 = 0
    metric5 = 0

    _ifindex = None
    _ifname = None

    _properties = (
        {'id':'routemask', 'type':'string', 'mode':''},
        {'id':'nexthopip', 'type':'string', 
            'mode':'', 'setter':'setNextHopIp'},
        {'id':'routeproto', 'type':'string', 'mode':''},
        {'id':'routeage', 'type':'string', 'mode':''},
        {'id':'routetype', 'type':'string', 'mode':''},
        {'id':'metric1', 'type':'int', 'mode':''},
        {'id':'metric2', 'type':'int', 'mode':''},
        {'id':'metric3', 'type':'int', 'mode':''},
        {'id':'metric4', 'type':'int', 'mode':''},
        {'id':'metric5', 'type':'int', 'mode':''},
        ) 
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","routes")),
        ("interface", ToOne(ToMany,"Products.ZenModel.IpInterface","iproutes")),
        ("nexthop", ToOne(ToMany,"Products.ZenModel.IpAddress","clientroutes")),
        ("target", ToOne(ToMany,"Products.ZenModel.IpNetwork","clientroutes")),
        )

    security = ClassSecurityInfo()

    ipcheck = re.compile(r'^127\.|^0\.0\.|^169\.254\.|^224\.|^::1$|^fe80:|^ff').search

    def before_object_deleted_handler(self):
        device = self.device()
        if device and device._operation != 1:
            if self.interface():
                self.interface.removeRelation()
            if self.nexthop():
                self.nexthop.removeRelation()
            if self.target():
                self.target.removeRelation()
    
    def __getattr__(self, name):
        """
        Allow access to getNextHopIp() though the nexthopip attribute
        """
        if name == 'nexthopip':
            return self.getNextHopIp()
        else:
            raise AttributeError( name )
  

    security.declareProtected('View', 'getNextHopDeviceLink')
    def getNextHopDeviceLink(self):
        """
        Figure out which hop to return and if it's a relation build link
        """
        ipobj = self.nexthop()
        retval = "" 
        if ipobj:
            retval = ipobj.getDeviceLink()
        if not retval: retval = "None"
        return retval
            

    def getNextHopIpLink(self):
        """
        Return an <a> link to our next hop ip.
        """
        ipobj = self.nexthop()
        if not ipobj: return ""
        return ipobj.getPrimaryLink()

        
    security.declareProtected('View', 'getNextHopIp')
    def getNextHopIp(self):
        """
        Return our next hop ip (as string) if stored as object or locally.
        """
        ip = self._nexthop
        ipobj = self.nexthop()
        if ipobj: ip = ipobj.id
        return ip
 

    def getNextHopDevice(self):
        """
        Return the device to which this route points.
        """
        ipobj = self.nexthop()
        if ipobj: return ipobj.device()
        
    
    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """
        Return the interface name for this route as a string.
        If no interface is found return 'No Interface'.
        """
        if self._ifname is not None:
            return self._ifname
        elif self.interface():
            return self.interface().name()
        return "No Interface"

       
    security.declareProtected('Change Device', 'setNextHopIp')
    def setNextHopIp(self, nextHopIp):
        """
        If the nexthop is a 127. or 0. address store locally
        else link to it in the network hierarchy
        """
        self._nexthop = nextHopIp
        # We dont want to add an IpAddress object for this. We should
        # probably stop modeling this


    def matchTarget(self, ip):
        """
        Does this route target match the ip passed.
        """
        if self.target(): return self.target().hasIp(ip)      
            
    
    def setTarget(self, netip):
        """
        Set this route target netip in the form 10.0.0.0/24.
        """
        netid, netmask = netip.split('/')
        if localIpCheck(self, netip) or netmask == '0':
            self._target = netip
        else:
            networks = self.device().getNetworkRoot()
            net = networks.createNet(netid, netmask)
            self.target.addRelation(net)


    def getTarget(self):
        """
        Return the route target ie 0.0.0.0/0.
        """
        if self.target():
            return self.target().getNetworkName()
        else:
            return self._target


    def getTargetIp(self):
        """
        Return the target network Ip ie: 10.2.1.0
        """
        return self.getTarget().split("/")[0]

        
    def getTargetLink(self):
        """
        Return an <a> link to our target network.
        """
        if self.target(): 
            return self.target().urlLink()
        else:
            return self._target


    security.declareProtected('Change Device', 'setInterfaceIndex')
    def setInterfaceIndex(self, ifindex):
        """
        Set the interface relationship to the interface specified by the given
        index.  See also setInterfaceName()
        """
        self._ifindex = ifindex
        for int in self.os().interfaces():
            if int.ifindex == ifindex: break
        else:
            int = None
        if int: self.interface.addRelation(int)
        #else: log.warn("interface index:%s not found", ifindex)


    def getInterfaceIndex(self):
        """
        Return the index of the associated interface or None if no
        interface is found.
        """
        if self._ifindex is not None:
            return self._ifindex
        else:
            int = self.interface()
            if int:
                return int.ifindex


    security.declareProtected('Change Device', 'setInterfaceName')
    def setInterfaceName(self, intname):
        """
        Set the interface relationship to the interface specified by the given
        name.  See also setInterfaceIndex()
        """
        self._ifname = intname
        try:
            int = filter(lambda i: i.name() == intname,
                    self.os().interfaces())[0]
            self.interface.addRelation(int)
        except IndexError:
            log.warn("interface '%s' not found", intname)


    def getInterfaceIp(self):
        """
        Retrieve ip of the associated interface
        """
        int = self.interface()
        if int: return int.getIp()
        return ""


InitializeClass(IpRouteEntry)
