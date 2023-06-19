##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """IpNetwork

IpNetwork represents an IP network which contains
many IP addresses.
"""

import math
import transaction
from xml.dom import minidom
import logging
log = logging.getLogger('zen')

from ipaddr import IPAddress, IPNetwork

from BTrees.OOBTree import OOBTree
from OFS.SimpleItem import SimpleItem

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.interfaces import IObjectEventsSubscriber

from Products.Jobber.zenjobs import app
from Products.ZenUtils.IpUtil import *
from Products.ZenRelations.RelSchema import *
from IpAddress import IpAddress
from DeviceOrganizer import DeviceOrganizer

from Products.ZenModel.Exceptions import *

from Products.ZenUtils.path import binPath
from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader, executeCommand
from Products.ZenUtils import NetworkTree
from Products.ZenUtils.Utils import unused, unpublished, edgesToXML
from Products.Jobber.jobs import SubprocessJob
from Products.ZenWidgets import messaging

from zope.event import notify
from zope.interface import implements

from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.indexable import IpNetworkIndexable
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr



class NetworkCache(SimpleItem):
    """
        We need to be able to quickly find if a network is already in Zenoss. Searching in the
        zcatalogs or solr decreases modeling performance. To work around this, we will have a
        network cache per Network root (by default dmd.Networks and dmd.IPv6Networks
        unless multirealm is installed). This cache will be an OOBtree with the following structure:

        OOBTree   { key: decimal net ip   value: { Network paths starting at the decimal ip } }

        When searching IpAddresses we will also use the network cache.
        If an Ip exists in Zenoss its network will have to exist, and then we will traverse
        the ipaddresses of the network (if it exists)
    """

    def __init__(self):
        self.cache = OOBTree()

    def get_key(self, netip, netmask):
        ip = netFromIpAndNet(netip, netmask)
        return ipToDecimal(ip)

    def _get_netmask_range(self, ip):
        netmask_range = range(8, 30+1)
        if get_ip_version(ip) == 6:
            netmask_range = range(48, 64+1)
        return netmask_range

    def _get_net(self, netip, netmask, basenet, context):
        net_obj = None
        key = self.get_key(netip, netmask)
        net_paths = self.cache.get(key, ())
        toDelete = []
        for net_path in net_paths:
            try:
                net = context.dmd.unrestrictedTraverse(net_path)
                if net.getNetworkRoot() == basenet and net.netmask == netmask:
                    net_obj = net
                    break
            except KeyError:
                toDelete.append(net_path)
                net_obj = None
        for net_path in toDelete:
            self.delete_net(key, net_path)
        return net_obj

    def get_net(self, netip, netmask, basenet, context):
        net_obj = None
        if netmask:
            net_obj = self._get_net(netip, netmask, basenet, context)
        else:
            netmask_range = self._get_netmask_range(netip)
            for mask in sorted(netmask_range, reverse=True):
                net_obj = self._get_net(netip, mask, basenet, context)
                if net_obj:
                    break
        return net_obj

    def add_net(self, net_obj):
        if net_obj:
            net_key = self.get_key(net_obj.id, net_obj.netmask)
            net_value = "/".join(net_obj.getPrimaryPath())
            nets = self.cache.get(net_key, set())
            nets.add(net_value)
            self.cache[net_key] = nets

    def delete_net(self, net_key, net_path):
        if net_key in self.cache:
            nets = self.cache.get(net_key)
            if net_path in nets:
                nets.remove(net_path)
                self.cache[net_key] = nets

    def delete_net_obj(self, net_obj):
        net_key = self.get_key(net_obj.id, net_obj.netmask)
        net_path = "/".join(net_obj.getPrimaryPath())
        self.delete_net(net_key, net_path)

    def _get_ip(self, ip, netmask, basenet, context):
        ip_obj = None
        # Lets check if the network exists first.
        net_ip = netFromIpAndNet(ip, netmask)
        net_obj = self.get_net(net_ip, netmask, basenet, context=context)
        if net_obj is not None: # Network does not exist so neither does the ip
            for existing_ip in net_obj.ipaddresses.objectValuesGen(): # traverse ip addresses looking for the one
                if existing_ip.id == ip:
                    ip_obj = existing_ip
                    break
        return ip_obj

    def get_ip(self, ip, netmask, basenet, context):
        """ Returns IpAddress object for ip if found, else None """
        ip_obj = None
        if netmask:
            ip_obj = self._get_ip(ip, netmask, basenet, context)
        else:
            netmask_range = self._get_netmask_range(ip)
            for mask in sorted(netmask_range, reverse=True):
                ip_obj = self._get_ip(ip, mask, basenet, context)
                if ip_obj:
                    break
        return ip_obj

    def get_subnets_paths(self, net_obj):
        """
        returns net_obj's subnets
        """
        subnets = []
        if net_obj:
            net = IPNetwork(ipunwrap(net_obj.id)) # addr.IPNetwork
            first_decimal_ip = long(int(net.network))
            last_decimal_ip = long(first_decimal_ip + math.pow(2, net.max_prefixlen - net_obj.netmask) - 1)
            for net_uids in self.cache.values(min=first_decimal_ip, max=last_decimal_ip, excludemin=True, excludemax=True):
                subnets.extend(net_uids)
        return subnets


def manage_addIpNetwork(context, id, netmask=24, REQUEST = None, version=4):
    """make a IpNetwork"""
    net = IpNetwork(id, netmask=netmask, version=version)
    context._setObject(net.id, net)
    if id.endswith("Networks"):
        net = context._getOb(net.id)
        net.dmdRootName = id
        net.buildZProperties()
        net.createCatalog()
        net.initialize_network_cache(net)
        #manage_addZDeviceDiscoverer(context)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


addIpNetwork = DTMLFile('dtml/addIpNetwork',globals())


# When an IP is added the default location will be
# into class A->B->C network tree
defaultNetworkTree = (32,)

class IpNetwork(DeviceOrganizer, IpNetworkIndexable):
    """IpNetwork object"""

    implements(IObjectEventsSubscriber)

    isInTree = True

    buildLinks = True

    # Index name for IP addresses
    default_catalog = 'ipSearch'

    portal_type = meta_type = 'IpNetwork'

    version = 4

    _properties = (
        {'id':'netmask', 'type':'int', 'mode':'w'},
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'version', 'type':'int', 'mode':'w'},
        )

    _relations = DeviceOrganizer._relations + (
        ("ipaddresses", ToManyCont(ToOne, "Products.ZenModel.IpAddress", "network")),
        ("clientroutes", ToMany(ToOne,"Products.ZenModel.IpRouteEntry","target")),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "networks")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'IpNetwork',
            'meta_type'      : 'IpNetwork',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'IpNetwork_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addIpNetwork',
            'immediate_view' : 'viewNetworkOverview',
            'actions'        :
            (
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewNetworkOverview'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'zProperties'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Manage DMD",)
                },
            )
          },
        )

    security = ClassSecurityInfo()

    NETWORK_CACHE_ATTR = "network_cache"

    def __init__(self, id, netmask=24, description='', version=4):
        if id.find("/") > -1: id, netmask = id.split("/",1)
        DeviceOrganizer.__init__(self, id, description)
        if not id.endswith("Networks"):
            checkip(id)
        self.netmask = maskToBits(netmask)
        self.version = version
        self.description = description
        self.title = ipunwrap(id)
        self.dmdRootName = "Networks"
        if version == 6:
            self.dmdRootName = "IPv6Networks"

    #----------------------------------------------------------
    #    Methods related to network cache
    #----------------------------------------------------------

    def initialize_network_cache(self, network_root):
        if hasattr(network_root, self.NETWORK_CACHE_ATTR):
            setattr(network_root, self.NETWORK_CACHE_ATTR, None)
        network_cache = NetworkCache()
        setattr(network_root, self.NETWORK_CACHE_ATTR, network_cache)
        for net in network_root.getSubNetworks():
            network_cache.add_net(net)

    def create_network_caches(self):
        """
        We will have a network cache per Network root (by default
        dmd.Networks and dmd.IPv6Networks unless multirealm is installed)
        { key: decimal net ip   value: [ Network paths starting at the decimal ip }
        """
        # ipv4 tree
        ip4_networks = self.getNetworkRoot(4)
        self.initialize_network_cache(ip4_networks)
        # ipv6 tree
        ip6_networks = self.getNetworkRoot(6)
        self.initialize_network_cache(ip6_networks)

    def get_network_cache(self, version=None):
        if not hasattr(self.getNetworkRoot(version), self.NETWORK_CACHE_ATTR):
            self.initialize_network_cache(self.getNetworkRoot(version))
        return getattr(self.getNetworkRoot(version), self.NETWORK_CACHE_ATTR)

    #----------------------------------------------------------
    #    IObjectEventsSubscriber Methods
    #----------------------------------------------------------

    def before_object_deleted_handler(self):
        if isip(self.id):
            self.get_network_cache().delete_net_obj(self)

    def after_object_added_or_moved_handler(self):
        if isip(self.id):
            self.get_network_cache().add_net(self)

    def object_added_handler(self):
        if isip(self.id):
            self.get_network_cache().add_net(self)

    #----------------------------------------------------------

    security.declareProtected(ZEN_CHANGE_NET, 'manage_addIpNetwork')
    def manage_addIpNetwork(self, newPath, REQUEST=None):
        """
        From the GUI, create a new subnet (if necessary)
        """
        net = self.createNet(newPath)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(net.absolute_url_path())

    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        if id.find("/") > -1: id, netmask = id.split("/",1)
        return super(IpNetwork, self).checkValidId(id, prep_id)


    def getNetworkRoot(self, version=None):
        """This is a hook method do not remove!"""
        if not isinstance(version, int):
            version = self.version
        if version is 6:
            return self.dmd.getDmdRoot("IPv6Networks")
        return self.dmd.getDmdRoot("Networks")

    def _get_smallest_mask(self, version):
        smallest_netmask = 8
        if version == 6:
            smallest_netmask = 48
        return smallest_netmask

    def _find_parent(self, net_ip, netmask):
        """
        Search for an existing network that is a supernet of netip/netmask
        """
        smallest_netmask = self._get_smallest_mask(self.version)
        parent = None
        for mask in xrange(netmask-1, smallest_netmask - 1, -1):
            parent_net_ip = netFromIpAndNet(net_ip, mask)
            netobj = self.get_network_cache().get_net(parent_net_ip, mask, self.getNetworkRoot(), context=self)
            if netobj: # We found a parent!
                parent = netobj
                break
        return parent

    def _get_default_network_tree(self, netip, netmask):
        """
        return the network tree to create based on 'zDefaultNetworkTree'

        'zDefaultNetworkTree' : list of netmask numbers to use when creating network containers.
                                Default is 24, 32 which will make /24 networks at the top level 
                                of the networks tree if a network is smaller than /24

        Example: If zDefaultNetworkTree is (24, 32) any net we need to create with netmask >=24
                 needs to be a child of the net/24
                 example_net: 10.10.10.128/25 will create the following net tree
                                10.10.10.0/24
                                    10.10.10.128/25
        """
        network_tree = []
        net_ip_obj = IPAddress(ipunwrap_strip(netip))
        if net_ip_obj.version == 4:
            for mask in getattr(self, 'zDefaultNetworkTree', defaultNetworkTree):
                network_tree.append(int(mask))
        else:
            # ISPs are supposed to provide the 48-bit prefix to orgs (RFC 3177)
            network_tree.append(48)

        if net_ip_obj.max_prefixlen not in network_tree:
            network_tree.append(net_ip_obj.max_prefixlen)

        return list(set(network_tree)) # just in case user gave duplicates

    def _parse_netip_and_netmask(self, netip, netmask):
        """ validates net ip and network """
        if '/' in  netip:
            netip, netmask = netip.split("/",1)

        checkip(netip)
        ipobj = IPAddress(ipunwrap_strip(netip))
        try:
            netmask = int(netmask)
        except (TypeError, ValueError):
            netmask = None
        biggest_netmask = ipobj.max_prefixlen if ipobj.version==4 else 64+1 
        netmask = netmask if netmask > 0  and netmask < biggest_netmask else None
        return netip, netmask, ipobj.version

    security.declareProtected(ZEN_ADD, 'createNet')
    def createNet(self, netip, netmask=None):
        """
        Return and create if necessary network.  netip is in the form
        1.1.1.0/24 or with netmask passed as parameter.  Subnetworks created
        based on the zParameter zDefaulNetworkTree.
        Called by IpNetwork.createIp
        If the netmask is invalid, then a netmask of 24 is assumed.

        @param netip: network IP address start
        @type netip: string
        @param netmask: network mask
        @type netmask: integer
        @todo: investigate IPv6 issues
        """
        netip, netmask, version = self._parse_netip_and_netmask(netip, netmask)

        # if netmask is None it will look for the net in all possible nets
        #
        netobj = self.get_network_cache(version).get_net(netip, netmask, self.getNetworkRoot(), context=self)

        if netobj is None:
            # Network does not exist. Create a new network
            if not netmask:
                netmask = get_default_netmask(netip)

            # Let's find a parent of the new net
            parent_mask = -1
            parent_net = self._find_parent(netip, netmask)
            if parent_net is None:
                parent_net = self.getNetworkRoot(version=version)
            else:
                parent_mask = parent_net.netmask

            # For netmasks greater than a config parameter we need to also create
            # the super networks. Ex for netmasks >= 24 we need to create the net with netmask
            # 24 and then a subnetwork of it with the requested netmask
            #
            default_net_tree = self._get_default_network_tree(netip, netmask)

            # filter net tree to create, we only need masks greater than the parent's 
            # and smaller than the the one we want to add
            network_tree = filter(lambda m: m > parent_mask and m < netmask, default_net_tree)
            network_tree.append(netmask)
            network_tree = sorted(network_tree)

            # We need to create the networks with masks in network_tree which
            # includes the net we wanted to create in the first place
            #
            for mask in network_tree:
                subnet_ip = netFromIpAndNet(netip, mask)
                subnet = parent_net.addSubNetwork(subnet_ip, mask)
                self.get_network_cache(version).add_net(subnet) # update the cache

                # check if any of the existing subnets of parent_net
                # is a subnet of the new net subnet. If so, move appropriately
                self.rebalance(parent_net, subnet)
                parent_net = netobj = subnet # prepare for next iteration

        return netobj

    security.declareProtected(ZEN_MANAGE_DMD, 'rebalance')
    def rebalance(self, netobjParent, netobj):
        """
        Look for children of netobjParent that could be subnets of the newly added net netobj
        and move them to the right place in the network tree
        """

        # Who can be a subnet of netobj ? networks whose decimal ip is between within netobj
        # ip range get all the nets that are a subnet of netobj
        all_subnets_paths = self.get_network_cache(netobj.version).get_subnets_paths(netobj)

        # keep only the ones that are at the same level as netobj
        parent_path = "/".join(netobjParent.getPrimaryPath())
        netobj_depth = len(netobj.getPrimaryPath())

        same_level_subnets_ids = []
        for subnet_path in all_subnets_paths:
            splitted = subnet_path.split("/")
            if len(splitted) == netobj_depth and parent_path in subnet_path:
                subnet_id = splitted[-1]
                same_level_subnets_ids.append(subnet_id)

        if same_level_subnets_ids:
            netobjPath = netobj.getOrganizerName()[1:]
            netobjParent.moveOrganizer(netobjPath, same_level_subnets_ids)

    def findNet(self, netip, netmask=None):
        """
        Find and return the subnet of this IpNetwork that matches the requested
        netip and netmask.
        """
        netip, netmask, version = self._parse_netip_and_netmask(netip, netmask)
        return self.get_net_from_cache(ipunwrap(netip), netmask)

    def getNet(self, ip, netmask=None):
        """ Return the net starting form the Networks root for ip. """
        return self.get_net_from_cache(ipunwrap(ip), netmask)

    def get_net_from_cache(self, netip, netmask=None):
        return self.get_network_cache().get_net(netip, netmask, self.getNetworkRoot(), context=self)

    def get_net_from_catalog(self, ip):
        """
        Search in the network tree the IpNetwork ip belongs to.
        return None if the network is not found
        """
        net = None
        cat = IModelCatalogTool(self.getNetworkRoot())
        decimal_ip = ipToDecimal(ip)
        query = {}
        query["firstDecimalIp"] = "[ * TO {0} ]".format(decimal_ip)
        query["lastDecimalIp"]  = "[ {0} TO * ]".format(decimal_ip)
        query["objectImplements"] = "Products.ZenModel.IpNetwork.IpNetwork"
        fields = [ "firstDecimalIp", "lastDecimalIp" ]
        result = cat.search(query=query, fields=fields)
        if result.total > 0:
            # networks found. if more than network is found, return the one
            # whose lastDecimalIp - firstDecimalIp is the smallest
            net_brains_tuples = [ ( net_brain, long(net_brain.lastDecimalIp) - long(net_brain.firstDecimalIp) ) for net_brain in result.results ]
            net_brain_tuple = min(net_brains_tuples, key=lambda x: x[1])
            net = net_brain_tuple[0].getObject()
        return net

    security.declareProtected(ZEN_ADD, 'createIp')
    def createIp(self, ip, netmask=None):
        """
        Return an ip and create if nessesary in a hierarchy of
        subnetworks based on the zParameter zDefaulNetworkTree.
        """
        network_cache = self.get_network_cache()

        # ip_obj = network_cache.get_ip(ip, netmask, context=self)
        ip_obj = self.findIp(ip, netmask)
        if not ip_obj: # Ip does not exists
            if not netmask:
                netmask = get_default_netmask(ip)
            net_obj = network_cache.get_net(ip, netmask, self.getNetworkRoot(), context=self)
            if net_obj is None: # Network does not exist
                net_obj = self.createNet(ip, netmask)
            ip_obj = net_obj.addIpAddress(ip, netmask)
        return ip_obj

    def _search_ip_in_catalog(self, ip):
        """ Return list of brains that match ip """
        cat = IModelCatalogTool(self.getNetworkRoot())
        query = {}
        query["objectImplements"] = "Products.ZenModel.IpAddress.IpAddress"
        query["id"] = ipwrap(ip)
        search_result = cat.search(query=query)
        return [ brain for brain in search_result.results ]

    def freeIps(self):
        """Number of free Ips left in this network.
        """
        freeips = 0
        try:
            net = IPNetwork(ipunwrap(self.id))
            freeips = int(math.pow(2, net.max_prefixlen - self.netmask) - self.countIpAddresses())
            if self.netmask > net.max_prefixlen:
                return freeips
            return freeips - 2
        except ValueError:
            for net in self.children():
                freeips += net.freeIps()
            return freeips

    def hasIp(self, ip):
        """
        Could this network contain this IP?
        """
        net = IPNetwork(ipunwrap(self.id))
        start = long(int(net.network))
        end = start + math.pow(2, net.max_prefixlen - self.netmask)
        return start <= numbip(ip) < end

    def fullIpList(self):
        """Return a list of all IPs in this network.
        """
        net = IPNetwork(ipunwrap(self.id))
        if (self.netmask == net.max_prefixlen): return [self.id]
        ipnumb = long(int(net))
        maxip = math.pow(2, net.max_prefixlen - self.netmask)
        start = int(ipnumb+1)
        end = int(ipnumb+maxip-1)
        return map(strip, range(start,end))


    security.declareProtected(ZEN_DELETE, 'deleteUnusedIps')
    def deleteUnusedIps(self):
        """Delete ips that are unused in this network.
        """
        for ip in self.ipaddresses():
            if ip.device(): continue
            self.ipaddresses.removeRelation(ip)


    def defaultRouterIp(self):
        """Return the ip of the default router for this network.
        It is based on zDefaultRouterNumber which specifies the sequence
        number that locates the router in this network.  If:
        zDefaultRouterNumber==1 for 10.2.1.0/24 -> 10.2.1.1
        zDefaultRouterNumber==254 for 10.2.1.0/24 -> 10.2.1.254
        zDefaultRouterNumber==1 for 10.2.2.128/25 -> 10.2.2.129
        zDefaultRouterNumber==126 for 10.2.2.128/25 -> 10.2.2.254
        """
        roffset = getattr(self, "zDefaultRouterNumber", 1)
        return strip((numbip(self.id) + roffset))


    def getNetworkName(self):
        """return the full network name of this network"""
        return "%s/%d" % (self.id, self.netmask)


    security.declareProtected(ZEN_VIEW, 'primarySortKey')
    def primarySortKey(self):
        """
        Sort by the IP numeric

        >>> net = dmd.Networks.addSubNetwork('1.2.3.0', 24)
        >>> net.primarySortKey()
        16909056
        """
        return numbip(self.id)

    security.declareProtected(ZEN_CHANGE_NET, 'addSubNetwork')
    def addSubNetwork(self, ip, netmask=24):
        """Return and add if neccesary subnetwork to this network.
        """
        netobj = self.getSubNetwork(ip)
        ip_id = ipwrap(ip)
        if not netobj:
            net = IpNetwork(ip_id, netmask=netmask, version=self.version)
            self._setObject(ip_id, net)
        elif netobj.netmask > netmask: # ex 10.1.0.0/12 exists and we need to add 10.0.0.0/8
            self._operation = 1 # Do we need this?
            self._delObject(ip_id) # remove ref to old net with greater mask
            new_net = IpNetwork(ip_id, netmask=netmask, version=self.version)
            self._setObject(ip_id, new_net)
            new_net = self._getOb(ip_id)
            netobj = aq_base(netobj)
            log.info(
                "Adding %s as supernet of %s",
                new_net.getNetworkName(), netobj.getNetworkName(),
            )
            new_net._setObject(ip_id, netobj)
            ips = filter(
                lambda n: isinstance(n, IpAddress) and n.interface(),
                netobj.getSubObjects(),
            )
            for i in ips:
                i.interface().ipaddresses._setObject(i.id, i)
            mips = filter(
                lambda n: isinstance(n, IpAddress) and n.manageDevice(),
                netobj.getSubObjects(),
            )
            for i in mips:
                i.manageDevice().ipaddress.addRelation(i)

        return self.getSubNetwork(ip)

    security.declareProtected(ZEN_VIEW, 'getSubNetwork')
    def getSubNetwork(self, ip):
        """get an ip on this network"""
        return self._getOb(ipwrap(ip), None)


    def getSubNetworks(self):
        """Return all network objects below this one.
        """
        nets = self.children()
        for subgroup in self.children():
            nets.extend(subgroup.getSubNetworks())
        return nets

    security.declareProtected(ZEN_CHANGE_NET, 'addIpAddress')
    def addIpAddress(self, ip, netmask=24):
        """add ip to this network and return it"""
        ipobj = IpAddress(ip,netmask)
        self.ipaddresses._setObject(ipwrap(ip), ipobj)
        return self.getIpAddress(ip)


    security.declareProtected(ZEN_VIEW, 'getIpAddress')
    def getIpAddress(self, ip):
        """get an ip on this network"""
        return self.ipaddresses._getOb(ipwrap(ip), None)

    security.declareProtected(ZEN_CHANGE_NET, 'manage_deleteIpAddresses')
    def manage_deleteIpAddresses(self, ipaddresses=(), REQUEST=None):
        """Delete ipaddresses by id from this network.
        """
        for ipaddress in ipaddresses:
            ip = self.getIpAddress(ipaddress)
            self.ipaddresses.removeRelation(ip)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_VIEW, 'countIpAddresses')
    def countIpAddresses(self, inuse=False):
        """get an ip on this network"""
        if inuse:
            # When there are a large number of IPs this code is too slow
            # we either need to cache all /Status/Ping events before hand
            # and then integrate them with the list of IPs
            # or blow off the whole feature.  For now we just set the
            # default to not use this code.  -EAD
            count = len(filter(lambda x: x.getStatus() == 0,self.ipaddresses()))
        else:
            count = self.ipaddresses.countObjects()
        for net in self.children():
            count += net.countIpAddresses(inuse)
        return count

    security.declareProtected(ZEN_VIEW, 'countDevices')
    countDevices = countIpAddresses


    def getAllCounts(self, devrel=None):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        unused(devrel)
        counts = [
            self.ipaddresses.countObjects(),
            self._status("Ping", "ipaddresses"),
            self._status("Snmp", "ipaddresses"),
        ]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def pingStatus(self, devrel=None):
        """aggregate ping status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.pingStatus(self, "ipaddresses")


    def snmpStatus(self, devrel=None):
        """aggregate snmp status for all devices in this group and below"""
        unused(devrel)
        return DeviceOrganizer.snmpStatus(self, "ipaddresses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceOrganizer.getSubDevices(self, filter, "ipaddresses")

    def find_ip(self, ip):
        """
        Looks for the ipaddress in the catalog.
        Avoid calling this method during modeling if possible
        """
        brains = self._search_ip_in_catalog(ip)
        ip_obj = None
        if len(brains) > 0:
            if len(brains) == 1:
                ip_obj = brains[0].getObject()
            else:
                raise IpAddressConflict( "IP address conflict for IP: %s" % ip )
        return ip_obj

    def findIp(self, ip, netmask=None):
        """
        Search for the ip in the network cache.
        Use this method for modeling if possible
        """
        if isip(ip):
            return self.get_network_cache().get_ip(ip, netmask, self.getNetworkRoot(), context=self)
        else: # need to look in the catalog
            return self.find_ip(ip)

    security.declareProtected(ZEN_MANAGE_DMD, 'buildZProperties')
    def buildZProperties(self):
        if self.version == 6:
            nets = self.getDmdRoot("IPv6Networks")
        else:
            nets = self.getDmdRoot("Networks")
        if getattr(aq_base(nets), "zDefaultNetworkTree", False):
            return
        nets._setProperty("zDefaultNetworkTree", (64,128) if nets.id == "IPv6Networks" else (24,32), type="lines")
        nets._setProperty("zDrawMapLinks", True, type="boolean")
        nets._setProperty("zAutoDiscover", True, type="boolean")
        nets._setProperty("zPingFailThresh", 168, type="int")
        nets._setProperty("zIcon", "/zport/dmd/img/icons/network.png")
        nets._setProperty("zPreferSnmpNaming", False, type="boolean")
        nets._setProperty("zSnmpStrictDiscovery", False, type="boolean")

    security.declareProtected(ZEN_MANAGE_DMD, 'reIndex')
    def reIndex(self):
        """Go through all ips in this tree and reindex them."""
        for net in self.getSubNetworks():
            for ip in net.ipaddresses():
                notify(IndexingEvent(ip))

    security.declareProtected(ZEN_ADD, 'createCatalog')
    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.Zuul.catalog.legacy import LegacyCatalogAdapter
        if hasattr(self, self.default_catalog):
            self._delObject(self.default_catalog)
        setattr(self, self.default_catalog, LegacyCatalogAdapter(self, self.default_catalog))

    security.declareProtected(ZEN_ADD, 'discoverNetwork')
    def discoverNetwork(self, REQUEST=None):
        """
        """
        path = '/'.join(self.getPrimaryPath()[4:])
        return self.discoverDevices([path], REQUEST=REQUEST)

    security.declareProtected(ZEN_ADD, 'discoverDevices')
    def discoverDevices(self, organizerPaths=None, REQUEST = None):
        """
        Load a device into the database connecting its major relations
        and collecting its configuration.
        """
        xmlrpc = isXmlRpc(REQUEST)

        if not organizerPaths:
            if xmlrpc: return 1
            return self.callZenScreen(REQUEST)

        zDiscCommand = "empty"

        from Products.ZenUtils.ZenTales import talesEval

        orgroot = self.getNetworkRoot()
        for organizerName in organizerPaths:
            organizer = orgroot.getOrganizer(organizerName)
            if organizer is None:
                if xmlrpc: return 1 # XML-RPC error
                log.error("Couldn't obtain a network entry for '%s' "
                            "-- does it exist?", organizerName)
                continue

            zDiscCommand = getattr(organizer, "zZenDiscCommand", None)
            if zDiscCommand:
                cmd = talesEval('string:' + zDiscCommand, organizer).split(" ")
            else:
                cmd = ["zendisc", "run", "--net", organizer.getNetworkName()]
                if getattr(organizer, "zSnmpStrictDiscovery", False):
                    cmd += ["--snmp-strict-discovery"]
                if getattr(organizer, "zPreferSnmpNaming", False):
                    cmd += ["--prefer-snmp-naming"]
            zd = binPath('zendisc')
            zendiscCmd = [zd] + cmd[1:]
            status = self.dmd.JobManager.addJob(SubprocessJob,
                description="Discover devices in network %s" % organizer.getNetworkName(),
                args=(zendiscCmd,))

        log.info('Done')

        if REQUEST and not xmlrpc:
            REQUEST.RESPONSE.redirect('/zport/dmd/JobManager/joblist')

        if xmlrpc: return 0


    def setupLog(self, response):
        """setup logging package to send to browser"""
        from logging import StreamHandler, Formatter
        root = logging.getLogger()
        self._v_handler = StreamHandler(response)
        fmt = Formatter("""<tr class="tablevalues">
        <td>%(asctime)s</td><td>%(levelname)s</td>
        <td>%(name)s</td><td>%(message)s</td></tr>
        """, "%Y-%m-%d %H:%M:%S")
        self._v_handler.setFormatter(fmt)
        root.addHandler(self._v_handler)
        root.setLevel(10)


    def clearLog(self):
        alog = logging.getLogger()
        if getattr(self, "_v_handler", False):
            alog.removeHandler(self._v_handler)


    def loaderFooter(self, response):
        """add navigation links to the end of the loader output"""
        response.write("""<tr class="tableheader"><td colspan="4">
            Navigate to network <a href=%s>%s</a></td></tr>"""
            % (self.absolute_url_path(), self.id))
        response.write("</table></body></html>")

    security.declareProtected(ZEN_VIEW, 'getXMLEdges')
    def getXMLEdges(self, depth=1, filter='/', start=()):
        """ Gets XML """
        if not start: start=self.id
        edges = NetworkTree.get_edges(self, depth,
                                      withIcons=True, filter=filter)
        return edgesToXML(edges, start)

    def getIconPath(self):
        """ gets icon """
        try:
            return self.primaryAq().zIcon
        except AttributeError:
            return '/zport/dmd/img/icons/noicon.png'


    @unpublished
    def urlLink(self, text=None, url=None, attrs={}):
        """
        Return an anchor tag if the user has access to the remote object.
        @param text: the text to place within the anchor tag or string.
                     Defaults to the id of this object.
        @param url: url for the href. Default is getPrimaryUrlPath
        @type attrs: dict
        @param attrs: any other attributes to be place in the in the tag.
        @return: An HTML link to this object
        @rtype: string
        """
        if not text:
            text = "%s/%d" % (self.id, self.netmask)
        if not self.checkRemotePerm("View", self):
            return text
        if not url:
            url = self.getPrimaryUrlPath()
        if len(attrs):
            return '<a href="%s" %s>%s</a>' % (url,
                ' '.join('%s="%s"' % (x,y) for x,y in attrs.items()),
                text)
        else:
            return '<a href="%s">%s</a>' % (url, text)

InitializeClass(IpNetwork)


class AutoDiscoveryJob(SubprocessJob):
    """
    Job encapsulating autodiscovery over a set of IP addresses.

    Accepts a list of strings describing networks OR a list of strings
    specifying IP ranges, not both. Also accepts a set of zProperties to be
    set on devices that are discovered.
    """
    name = 'AutoDiscoveryJob'
    def _run(self, nets=(), ranges=(), zProperties={}, collector='localhost'):
        # Store the nets and ranges
        self.nets = nets
        self.ranges = ranges

        # Store zProperties on the job
        if zProperties:
            self.setProperties(**zProperties)
        # Build the zendisc command setting zminion timeout to 6 hours.
        max_seconds = 6*60*60
        cmd = self.dmd.Monitors.getPerformanceMonitor(collector)._getZenDiscCommand(
            '', '/Discovered', collector, 1000, max_seconds=max_seconds)
        # strip out the device option since we are discovering for a network
        cmd = [c.replace(" -d ", "") for c in cmd if c != '-d']
        cmd.extend([
                '--parallel', '8',
                '--job', self.request.id
                   ])
        if not self.nets and not self.ranges:
            # Gotta have something
            self.log.error("Must pass in either a network or a range.")
        elif self.nets and self.ranges:
            # Can't have both
            self.log.error("Must pass in either networks or ranges, not both")
        else:
            if self.nets:
                for net in self.nets:
                    cmd.extend(['--net', net])
            elif self.ranges:
                for iprange in self.ranges:
                    cmd.extend(['--range', iprange])
            SubprocessJob._run(self, cmd)


app.register_task(AutoDiscoveryJob)

class IpNetworkPrinter(object):

    def __init__(self, out):
        """out is the output stream to print to"""
        self._out = out


class TextIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out IpNetwork hierarchy as text with indented lines.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        self._printIpNetworkLine(net)
        self._printTree(net)

    def _printTree(self, net, indent="  "):
        for child in net.children():
            self._printIpNetworkLine(child, indent)
            self._printTree(child, indent + "  ")
        for ipaddress in net.ipaddresses():
            args = (indent, ipaddress, ipaddress.__class__.__name__)
            self._out.write("%s%s (%s)\n" % args)

    def _printIpNetworkLine(self, net, indent=""):
        args = (indent, net.id, net.netmask, net.__class__.__name__)
        self._out.write("%s%s/%s (%s)\n" % args)


class PythonIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out the IpNetwork hierarchy as a python dictionary.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        tree = {}
        self._createTree(net, tree)
        from pprint import pformat
        self._out.write("%s\n" % pformat(tree))

    def _walkTree(self, net, tree):
        for child in net.children():
            self._createTree(child, tree)
        for ip in net.ipaddresses():
            key = (ip.__class__.__name__, ip.id, ip.netmask)
            tree[key] = True

    def _createTree(self, net, tree):
        key = (net.__class__.__name__, net.id, net.netmask)
        subtree = {}
        tree[key] = subtree
        self._walkTree(net, subtree)


class XmlIpNetworkPrinter(IpNetworkPrinter):
    """
    Prints out the IpNetwork hierarchy as XML.
    """

    def printIpNetwork(self, net):
        """
        Print out the IpNetwork and IpAddress hierarchy under net.
        """
        self._doc = minidom.parseString('<root/>')
        root = self._doc.documentElement
        self._createTree(net, root)
        self._out.write(self._doc.toprettyxml())

    def _walkTree(self, net, tree):
        for child in net.children():
            self._createTree(child, tree)
        for ip in net.ipaddresses():
            self._appendChild(tree, ip)

    def _createTree(self, net, tree):
        node = self._appendChild(tree, net)
        self._walkTree(net, node)

    def _appendChild(self, tree, child):
        node = self._doc.createElement(child.__class__.__name__)
        node.setAttribute("id", child.id)
        node.setAttribute("netmask", str(child.netmask))
        tree.appendChild(node)
        return node


class IpNetworkPrinterFactory(object):

    def __init__(self):
        self._printerFactories = {'text': TextIpNetworkPrinter,
                                  'python': PythonIpNetworkPrinter,
                                  'xml': XmlIpNetworkPrinter}

    def createIpNetworkPrinter(self, format, out):
        if format in self._printerFactories:
            factory = self._printerFactories[format]
            return factory(out)
        else:
            args = (format, self._printerFactories.keys())
            raise Exception("Invalid format '%s' must be one of %s" % args)
