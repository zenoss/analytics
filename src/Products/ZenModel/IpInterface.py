##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""IpInterface

IpInterface is a collection of devices and subsystems that make
up a business function
"""

import re
import copy
import logging
from itertools import chain
log = logging.getLogger("zen.IpInterface")

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from App.Dialogs import MessageDialog
from AccessControl import ClassSecurityInfo
from zope.event import notify
from zope.container.contained import ObjectMovedEvent

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import localIpCheck, localInterfaceCheck, convToUnits
from Products.ZenUtils.IpUtil import *

from ConfmonPropManager import ConfmonPropManager
from OSComponent import OSComponent
from Products.ZenModel.Exceptions import *

from Products.ZenModel.ZenossSecurity import *
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.events import IAfterIndexingEventSubscriber

from Products.Zuul.catalog.indexable import IpInterfaceIndexable
from Products.ZenModel.interfaces import IObjectEventsSubscriber
from zope.interface import implements


_IPADDRESS_CACHE_ATTR = "_v_ipaddresses"


def manage_addIpInterface(context, newId, userCreated, REQUEST = None):
    """
    Make a device via the ZMI
    """
    d = IpInterface(newId)
    context._setObject(newId, d)
    d = context._getOb(newId)
    d.interfaceName = newId
    if userCreated: d.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()
                                     +'/manage_main')

addIpInterface = DTMLFile('dtml/addIpInterface',globals())


class IpInterface(OSComponent, IpInterfaceIndexable):
    """
    IpInterface object
    """
    implements(IObjectEventsSubscriber, IAfterIndexingEventSubscriber)

    portal_type = meta_type = 'IpInterface'

    manage_editIpInterfaceForm = DTMLFile('dtml/manageEditIpInterface',
                                                        globals())

    # catalog to find interfaces that should be pinged
    # indexes are id and description
    #default_catalog = 'interfaceSearch'

    ifindex = '0'
    interfaceName = ''
    macaddress = ""
    type = ""
    description = ""
    mtu = 0
    speed = 0
    adminStatus = 0
    operStatus = 0
    duplex = 0
    _ipAddresses =  []



    _properties = OSComponent._properties + (
        {'id':'ips', 'type':'lines', 'mode':'w', 'setter':'setIpAddresses'},
        {'id':'interfaceName', 'type':'string', 'mode':'w'},
        {'id':'ifindex', 'type':'string', 'mode':'w'},
        {'id':'macaddress', 'type':'string', 'mode':'w'},
        {'id':'type', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
        {'id':'mtu', 'type':'int', 'mode':'w'},
        {'id':'speed', 'type':'long', 'mode':'w'},
        {'id':'adminStatus', 'type':'int', 'mode':'w'},
        {'id':'operStatus', 'type':'int', 'mode':'w'},
        {'id':'duplex', 'type':'int', 'mode':'w'},
        )

    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont,"Products.ZenModel.OperatingSystem","interfaces")),
        ("ipaddresses", ToMany(ToOne,"Products.ZenModel.IpAddress","interface")),
        ("iproutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","interface")),
        )

    zNoPropertiesCopy = ('ips','macaddress')

    localipcheck = re.compile(r'^127.|^0.|^::1$|^fe80:').search
    localintcheck = re.compile(r'^lo0').search

    defaultIgnoreTypes = ('Other', 'softwareLoopback', 'CATV MAC Layer')

    factory_type_information = (
        {
            'id'             : 'IpInterface',
            'meta_type'      : 'IpInterface',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpInterface_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpInterface',
            'immediate_view' : 'viewIpInterface',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewIpInterface'
                , 'permissions'   : (ZEN_VIEW,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def __init__(self, id, title = None):
        """
        Init OSComponent and set _ipAddresses to an empty list.
        """
        OSComponent.__init__(self, id, title)
        self._ipAddresses = []


    def _invalidate_ipaddress_cache(self):
        setattr(self, _IPADDRESS_CACHE_ATTR, None)

    security.declareProtected('View', 'viewName')
    def viewName(self):
        """
        Use the unmagled interface name for display
        """
        return self.interfaceName.rstrip('\x00') #Bogus fix for MS names
    name = primarySortKey = viewName

    def _setPropValue(self, id, value):
        """
        Override from PerpertyManager to handle checks and ip creation
        """
        self._wrapperCheck(value)
        if id == 'ips':
            self.setIpAddresses(value)
        else:
            setattr(self,id,value)
            if id == 'macaddress':
                notify(IndexingEvent(self))

    #------------------------------------------
    #--    ITreeSpanningComponent methods   --

    def get_indexable_peers(self):
        """  """
        return self.ipaddresses()

    #------------------------------------------
    #--    IObjectEventsSubscriber methods   --

    def after_object_added_or_moved_handler(self):
        self._invalidate_ipaddress_cache()
        self._update_device_macs(self.device(), self.macaddress)

    def before_object_deleted_handler(self):
        device = self.device()
        if device:
            macs = device.getMacAddressCache()
            try: 
                macs.remove(self.macaddress)
                notify(IndexingEvent(device, idxs=('macAddresses',), update_metadata=False))
            except KeyError:
                pass
            if device._operation != 1:
                if self.ipaddresses():
                    self.ipaddresses.removeRelation()
                if self.iproutes():
                    self.iproutes.removeRelation()

    def object_added_handler(self):
        self._update_device_macs(self.device(), self.macaddress)

    #------------------------------------------------
    #--    IAfterIndexingEventSubscriber methods   --
    def after_indexing_event(self, event):
        """
        @params event: IndexingEvent for whom we were called
        """
        if not event.triggered_by_zope_event:
            # when the event is triggers by zope, the
            # IObjectEventsSubscriber methods are called
            self._update_device_macs(self.device(), self.macaddress)

    #------------------------------------------

    def _update_device_macs(self, device, macaddress):
        if device and macaddress:
            if ( device.getMacAddressCache().add(macaddress) ):
                notify(IndexingEvent(device, idxs=('macAddresses',)))  # @TODO Should we remove the macs from the device?

    def index_object(self, idxs=None):
        """
        DEPRECATED  -  Override the default so that links are indexed.
        """
        super(IpInterface, self).index_object(idxs)

    def unindex_object(self):
        """
        DEPRECATED  -  Override the default so that links are unindexed.
        """
        super(IpInterface, self).unindex_object()
            
    def manage_deleteComponent(self, REQUEST=None):
        """
        Reindexes all the ip addresses on this interface
        after it has been deleted
        """
        device = self.device()
        ips = self.ipaddresses()
        super(IpInterface, self).manage_deleteComponent(REQUEST)
        for ip in ips:
            self.dmd.getDmdRoot("ZenLinkManager").remove_device_network_from_cache(device.getId(), ip.network().getPrimaryUrlPath())
        if device:
            notify(IndexingEvent(device, idxs=["path"])) # We need to delete the iface path from the device

    def manage_editProperties(self, REQUEST):
        """
        Override from propertiyManager so we can trap errors
        """
        try:
            return ConfmonPropManager.manage_editProperties(self, REQUEST)
        except IpAddressError as e:
            return   MessageDialog(
                title = "Input Error",
                message = e.args[0],
                action = "manage_main")


    def __getattr__(self, name):
        """
        Allow access to ipAddresses via the ips attribute
        """
        if name == 'ips':
            return self.getIpAddresses()
        else:
            raise AttributeError( name )


    def _prepIp(self, ip, netmask=24):
        """
        Split ips in the format 1.1.1.1/24 into ip and netmask.
        Default netmask is 24.
        """
        iparray = ip.split("/")
        if len(iparray) > 1:
            ip = iparray[0]
            checkip(ip)
            netmask = maskToBits(iparray[1])
        return ip, netmask


    def addIpAddress(self, ip, netmask=24):
        """
        Add an ip to the ipaddresses relationship on this interface.
        """
        self._invalidate_ipaddress_cache()
        networks = self.device().getNetworkRoot()
        ip, netmask = self._prepIp(ip, netmask)
        #see if ip exists already and link it to interface
        if not netmask:
            netmask = get_default_netmask(ip)
        ipobj = networks.findIp(ip, netmask)
        if ipobj:
            dev = ipobj.device()
            if dev and dev != self.device():
                log.warn("Adding IP Address %s to %s found it on device %s",
                         ip, self.getId(), dev.getId())
            self.ipaddresses.addRelation(ipobj)
        #never seen this ip make a new one in correct subnet
        else:
            ipobj = networks.createIp(ip, netmask)
            self.ipaddresses.addRelation(ipobj)
        notify(IndexingEvent(ipobj))
        if self.device():
            notify(IndexingEvent(self.device(), idxs=('path')))
        os = self.os()
        notify(ObjectMovedEvent(self, os, self.id, os, self.id))
        self.dmd.getDmdRoot("ZenLinkManager").add_device_network_to_cache(self.device().getId(), ipobj.network().getPrimaryUrlPath())



    def addLocalIpAddress(self, ip, netmask=24):
        """
        Add a locally stored ip. Ips like 127./8 are maintained locally.
        """
        (ip, netmask) = self._prepIp(ip, netmask)
        ip = ip + '/' + str(netmask)
        if not self._ipAddresses: self._ipAddresses = []
        if not ip in self._ipAddresses:
            self._invalidate_ipaddress_cache()
            self._ipAddresses = self._ipAddresses + [ip,]


    def clearIps(self, ips):
        """
        If no IPs are sent remove all in the relation
        """
        if not ips:
            self.removeRelation('ipaddresses')
            self._invalidate_ipaddress_cache()
            return True


    def setIpAddresses(self, ips):
        """
        Set a list of ipaddresses in the form 1.1.1.1/24 on to this
        interface. If networks for the ips don't exist they will be created.
        """
        if isinstance(ips, basestring): ips = [ips,]
        if self.clearIps(ips): return

        ipids = self.ipaddresses.objectIdsAll()
        localips = copy.copy(self._ipAddresses)
        for ip in ips:
            if not ip:
                continue
            if localIpCheck(self, ip) or localInterfaceCheck(self, self.id):
                if not ip in localips:
                    self.addLocalIpAddress(ip)
                else:
                    localips.remove(ip)
            else:
                # do this funky filtering because the id we have
                # is a primary id /zport/dmd/Networks... etc
                # and we are looking for just the IP part
                # we used the full id later when deleting the IPs
                rawip = ipFromIpMask(ipwrap(ip))
                ipmatch = filter(lambda x: x.find(rawip) > -1, ipids)
                if not ipmatch:
                    try:
                        self.addIpAddress(ip)
                    except IpAddressError:
                        log.info("Ignoring invalid IP address %s", rawip)
                elif len(ipmatch) == 1:
                    ipids.remove(ipmatch[0])


        #delete ips that are no longer in use
        dirty = False
        for ip in ipids:
            ipobj = self.ipaddresses._getOb(ip)
            self.removeRelation('ipaddresses', ipobj)
            dirty = True
            notify(IndexingEvent(ipobj))
        for ip in localips:
            dirty = True
            self._ipAddresses.remove(ip)

        # Invalidate the cache if we removed an ip.
        if dirty:
            self._invalidate_ipaddress_cache()

    def removeIpAddress(self, ip):
        """
        Remove an ipaddress from this interface.
        """
        for ipobj in self.ipaddresses():
            if ipobj.id == ip:
                self._invalidate_ipaddress_cache()
                self.ipaddresses.removeRelation(ipobj)
                notify(IndexingEvent(ipobj))
                return


    def getIp(self):
        """
        Return the first ip for this interface in the form: 1.1.1.1.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIp()
        elif len(self._ipAddresses):
            return self._ipAddresses[0].split('/')[0]


    def getIpSortKey(self):
        """
        Return the IP address as an integter for sorting purposes.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].primarySortKey()
        elif len(self._ipAddresses):
            return numbip(self._ipAddresses[0].split('/')[0])


    def getIpAddress(self):
        """
        Return the first IP address with its netmask ie: 1.1.1.1/24.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].getIpAddress()
        elif len(self._ipAddresses):
            return self._ipAddresses[0]


    def getIpAddressObj(self):
        """
        Return the first real IP address object or None if none are found.
        """
        if len(self.ipaddresses()):
            return self.ipaddresses()[0]


    def getIpAddressObjsGen(self):
        return chain(self.ipaddresses.objectValuesGen(), self._ipAddresses)


    def getIpAddressObjs(self):
        """
        Return a list of the ip objects on this interface.
        """
        return list(self.getIpAddressObjsGen())


    def getIpAddresses(self):
        """
        Return list of ip addresses as strings in the form 1.1.1.1/24.

        Because this is somewhat expensive to calculate, cache the
        result on a volatile attribute. This cache will only have the
        lifespan of this instance, but many operations (e.g., indexing)
        need it multiple times.
        """
        addrs = getattr(self, _IPADDRESS_CACHE_ATTR, None)
        if addrs is None:
            addrs = map(str, self.getIpAddressObjsGen())
            setattr(self, _IPADDRESS_CACHE_ATTR, addrs)
        return addrs


    def getNetwork(self):
        """
        Return the network for the first ip on this interface.
        """
        if self.ipaddresses.countObjects():
            return self.ipaddresses()[0].network()


    def getNetworkName(self):
        """
        Return the network name for the first ip on this interface.
        """
        net = self.getNetwork()
        if net: return net.getNetworkName()
        return ""


    def getNetworkLink(self):
        """
        Return the network link for the first ip on this interface.
        """
        if len(self.ipaddresses()):
            addr = self.ipaddresses.objectValuesAll()[0]
            if addr:
                if hasattr(aq_base(addr), 'network'):
                    if self.checkRemotePerm("View", addr.network):
                        return addr.network.getPrimaryLink()
                    else:
                        return addr.network.getRelatedId()
        else:
            return ""


    def getNetworkLinks(self):
        """
        Return a list of network links for each ip in this interface.
        """
        addrs = self.ipaddresses() + self._ipAddresses
        if addrs:
            links = []
            for addr in addrs:
                if hasattr(aq_base(addr), 'network'):
                    if self.checkRemotePerm('View', addr.network()):
                        links.append(addr.network.getPrimaryLink())
                    else:
                        links.append(addr.network.getRelatedId())
                else:
                    links.append("")
            return "<br/>".join(links)
        else:
            return ""


    security.declareProtected('View', 'getInterfaceName')
    def getInterfaceName(self):
        """
        Return the name of this interface.
        """
        if self.interfaceName: return self.interfaceName
        elif self.viewName(): return self.viewName()
        else: return "None"


    security.declareProtected('View', 'getInterfaceMacaddress')
    def getInterfaceMacaddress(self):
        """
        Return the mac address of this interface.
        """
        return self.macaddress


    def getRRDTemplateName(self):
        """
        Return the interface type as the target type name.
        """
        return self.prepId(self.type or "Unknown")


    def getRRDTemplates(self):
        """
        Return a list containing the appropriate RRDTemplate for this
        IpInterface. If none is found then the list will be empty.

        Order of preference if the interface supports 64bit counters.
            1. <type>_64
            2. ethernetCsmacd_64
            3. <type>
            4. ethernetCsmacd

        Order of preference if the interface doesn't support 64bit counters.
            1. <type>
            2. ethernetCsmacd
        """
        templateName = self.getRRDTemplateName()

        order = ['ethernetCsmacd']
        if templateName.endswith('_64'):
            order.insert(0, 'ethernetCsmacd_64')
            if templateName not in order:
                order.insert(0, templateName)
                order.insert(2, templateName[:-3])
        else:
            if templateName not in order:
                order.insert(0, templateName)

        for name in order:
            templates = []
            template = self.getRRDTemplateByName(name)
            if not template:
                continue
            replacement = self.getRRDTemplateByName(
                '{}-replacement'.format(name))

            if replacement and replacement not in templates:
                templates.append(replacement)
            else:
                templates.append(template)

            addition = self.getRRDTemplateByName(
                '{}-addition'.format(name))

            if addition and addition not in templates:
                templates.append(addition)
            if templates:
                return templates

        return []


    def monitored(self):
        '''
        Return True if this instance should be monitored. False
        otherwise.
        '''
        if self.adminStatus > 1:
            return False
        else:
            return super(IpInterface, self).monitored()


    def snmpIgnore(self):
        """
        Ignore interface that are administratively down.
        """
        # This must be based off the modeled admin status or zenhub could
        # lock itself up while building configurations.
        return self.adminStatus > 1 or self.monitor == False


    def getAdminStatus(self):
        """
        Get the current administrative state of the interface. 
        """
        return self.adminStatus


    def getAdminStatusString(self):
        """
        Return the current administrative state of the interface converted to
        its string version.
        """
        return {1: 'Up', 2: 'Down', 3: 'Testing'}.get(
            self.getAdminStatus(), 'Unknown')


    def getOperStatus(self):
        """
        Get the current operational state of the interface.
        """
        return self.operStatus

    def getOperStatusString(self):
        """
        Return the current operational state of the interface converted to
        its string version.
        """
        return {
            1: 'Up', 2: 'Down', 3: 'Testing', 5: 'Dormant', 6: 'Not Present',
            7: 'Lower Layer Down'}.get(
                self.getOperStatus(), 'Unknown')


    def getStatus(self, statClass=None):
        """
        Return the status number for this interface.
        """
        # Unknown status if we're not monitoring the interface.
        if self.snmpIgnore():
            return -1

        return super(IpInterface, self).getStatus()


    def niceSpeed(self):
        """
        Return a string that expresses self.speed in reasonable units.
        """
        if not self.speed:
            return 'Unknown'
        return convToUnits(self.speed, divby=1000, unitstr='bps')

    def deviceId(self):
        """
        The device id, for indexing purposes.
        """
        d = self.device()
        if d: return d.getPrimaryId()
        else: return None

    def interfaceId(self):
        """
        The interface id, for indexing purposes.
        """
        return self.getPrimaryId()

    def lanId(self):
        """
        pass
        """
        return 'None'

    def niceDuplex(self):
        """
        Return a string that expresses self.duplex into human readable format.
        """

        if self.duplex == 2:
            return 'halfDuplex'
        elif self.duplex == 3:
            return 'fullDuplex'
        return 'unknown'

InitializeClass(IpInterface)

