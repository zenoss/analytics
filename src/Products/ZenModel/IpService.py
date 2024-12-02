##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""IpService

IpService is a function provided by computer (like a server).  it
is defined by a protocol type (udp/tcp) and a port number.

"""

from App.special_dtml import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Products.ZenModel.ZenossSecurity import *

from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Service import Service
from Products.ZenModel.IpServiceClass import IpServiceClass
from Products.ZenUtils.IpUtil import isip

def manage_addIpService(context, id, protocol, port, userCreated=None, REQUEST=None):
    """
    Make an IP service entry
    """
    s = IpService(id)
    s.protocol = protocol
    s.port = int(port)
    args = {'protocol':protocol, 'port':int(port)}
    # Indexing is subscribed to ObjectAddedEvent, which fires
    # on _setObject, so we want to set service class first.
    s.__of__(context).setServiceClass(args)
    context._setObject(id, s)
    s = context._getOb(id)
    if userCreated: s.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main') 
    return s
    
addIpService = DTMLFile('dtml/addIpService',globals())


def getIpServiceKey(protocol, port):
    return "%s_%05d" % (protocol, port)


class IpService(Service):
    """
    IpService object
    """

    __pychecker__='no-override'

    portal_type = meta_type = 'IpService'

    protocols = ('tcp', 'udp')

    ipaddresses = []
    discoveryAgent = ""
    port = 0 
    protocol = ""
    manageIp = ""

    collectors = ('zenstatus',)

    _properties = (
        {'id':'port', 'type':'int', 'mode':'', 'setter': 'setPort',
         'description':"TCP port to check for this service."},
        {'id':'protocol', 'type':'string', 'mode':'', 'setter': 'setProtocol',
         'description':"Protocol (TCP or UPD) used by this service."},
        {'id':'ipaddresses', 'type':'lines', 'mode':'',
         'description':"IP addresses that this service is listening on."},
        {'id':'discoveryAgent', 'type':'string', 'mode':'',
         'description':"What process was used to discover this service."},
        {'id':'manageIp', 'type':'string', 'mode':'',
         'description':"The IP address to check for this service."},
        ) 
    _relations = Service._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","ipservices")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'ipServiceDetail',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'ipServiceDetail'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'ipServiceManage'
                , 'permissions'   : ("Manage DMD",)
                },
            )
         },
        )
    
    security = ClassSecurityInfo()


    def monitored(self):
        """
        Return monitored state of ipservice.  
        If service only listens on 127.0.0.1 return false.
        """
        if self.cantMonitor(): return False
        return super(IpService, self).monitored()
        

    def cantMonitor(self):
        """
        Return true if IpService only listens on 127.0.0.1, or if it is a UDP
        service.
        """
        return self.protocol == 'udp' \
                or ( len(self.ipaddresses) == 1 
                     and ("127.0.0.1" in self.ipaddresses or "::1" in self.ipaddresses))
                  


    def getInstDescription(self):
        """
        Return some text that describes this component.  Default is name.
        """
        return "%s-%d ips:%s" % (self.protocol, self.port, 
                                 ", ".join(self.ipaddresses))

        
    def setServiceClass(self, kwargs):
        """
        Set the service class based on a dict describing the service.
        Dict keys are be protocol and port
        """
        protocol = kwargs['protocol']
        port = kwargs['port']
        name = getIpServiceKey(protocol, port)
        path = "/IpService/"
        srvs = self.dmd.getDmdRoot("Services")
        srvclass = srvs.createServiceClass(name=name, path=path, 
                               factory=IpServiceClass, port=port)
        self.serviceclass.addRelation(srvclass)


    def getSendString(self):
        return self.getAqProperty("sendString")


    def getExpectRegex(self):
        return self.getAqProperty("expectRegex")


    def getServiceClass(self):
        """
        Return a dict like one set by IpServiceMap for services.
        """
        svc = self.serviceclass()
        if svc:
            return {'protocol': self.protocol, 'port': self.port }
        return {}


    def primarySortKey(self):
        return "%s-%05d" % (self.protocol, self.port)
    
    def getManageIp(self):
        """
        A service can listen on multiple interfaces on a device,
        and the interface it listens on may not be the same one 
        that is the manageIp for the device.

        @return: IP address to contact the service on
        @rtype: string
        """
        if self.manageIp:
            # List of IP address
            interfaces = self.getNonLoopbackIpAddresses()
            if self.manageIp in interfaces:
               if self.manageIp in self.ipaddresses or \
                  '0.0.0.0' in self.ipaddresses:
                   return self.manageIp
            # Oops! Our management IP is no longer here

        return self._getManageIp()

    def _getManageIp(self):
        """
        Pick an IP out of available choices.

        @return: IP address to contact the service on
        @rtype: string
        """
        if self.manageIp and isip(self.manageIp):
            return self.manageIp

        manage_ip = Service.getManageIp(self)
        bare_ip = manage_ip.split('/',1)[0]
        if bare_ip in self.ipaddresses:
            return bare_ip

        for ip in self.ipaddresses:
            if ip != '0.0.0.0' and ip != '127.0.0.1' and ip != '::1':
                return ip
        return bare_ip

    def setManageIp(self, manageIp):
        """
        Manually set the management IP address to check the
        service status.

        @parameter manageIp: IP address to check the service health
        @type manageIp: string
        """
        if not manageIp:
            return

        bare_ip = manageIp.split('/',1)[0]
        if not isip(bare_ip):
            return

        self.manageIp = bare_ip

    def unsetManageIp(self):
        """
        Remove a prevously set management IP address to check the
        service status.
        """
        self.manageIp = ''

    def getIpAddresses(self):
        """
        List the IP addresses to which we can contact the service.

        @return: list of IP addresses
        @rtype: array of strings
        """
        ips = [ ip for ip in self.ipaddresses \
            if ip != '0.0.0.0' and ip != '127.0.0.1' and ip != '::1']
        if not ips:
            ips = Service.getNonLoopbackIpAddresses(self)
            ips = [ x.split('/',1)[0] for x in ips ]
        return ips


    def getProtocol(self):
        return self.protocol

    def getPort(self):
        return self.port
        
    def getKeyword(self):
        sc = self.serviceclass()
        if sc: return sc.name

    def getDescription(self):
        sc = self.serviceclass()
        if sc: return sc.description

    def ipServiceClassUrl(self):
        sc = self.serviceclass()
        if sc: return sc.getPrimaryUrlPath()
    
    
    security.declareProtected('Manage DMD', 'manage_editService')
    def manage_editService(self, id=None, 
                        status=None, ipaddresses=None, 
                        manageIp=None, 
                        protocol=None, port=None,
                        description=None, 
                        monitor=False, severity=5, sendString="",
                        expectRegex="", REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if id:
            self.rename(id)
            if status: self.status = status
            self.ipaddresses = ipaddresses
            self.description = description
            self.protocol = protocol
            self._updateProperty('port', port)


            if protocol != self.protocol or port != self.port:
                self.setServiceClass({'protocol':protocol, 'port':int(port)})
        
        self.setManageIp(manageIp)

        msg = []
        msg.append(self.setAqProperty("sendString", sendString, "string"))
        msg.append(self.setAqProperty("expectRegex", expectRegex, "string"))
        self.index_object()
        
        return super(IpService, self).manage_editService(monitor, severity, 
                                        msg=msg,REQUEST=REQUEST)


InitializeClass(IpService)
