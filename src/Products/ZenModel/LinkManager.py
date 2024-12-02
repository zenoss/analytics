##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from itertools import ifilter, combinations
from collections import defaultdict

from Acquisition import aq_base

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo

from OFS.Folder import Folder
from BTrees.OOBTree import OOBTree

from json import dumps
from Products.AdvancedQuery import Eq
from Products.CMFCore.utils import getToolByName
from Products.ZenModel.Device import Device
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.NetworkTree import NetworkLink
from Products.ZenEvents.events2.processing import Manager
from Products.Zuul import getFacade
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr
from zenoss.protocols.protobufs.zep_pb2 import (SEVERITY_CRITICAL, SEVERITY_ERROR,
                                                SEVERITY_WARNING, SEVERITY_INFO,
                                                SEVERITY_DEBUG, SEVERITY_CLEAR)
from zenoss.protocols.protobufs.zep_pb2 import STATUS_NEW, STATUS_ACKNOWLEDGED

security = ClassSecurityInfo()

NODE_IDS = dict(
    layer_3 = {'IpNetwork':'networkId', 'Device':'deviceId'},
    layer_2 = {'LAN':'lanId', 'Device':'deviceId'}
)

def _getComplement(context, layer=3):
    key = 'layer_%d' % layer
    nodestuff = NODE_IDS[key]
    if not isinstance(context, basestring):
        try:
            context = nodestuff[context.meta_type]
        except KeyError:
            return None
    first, second = nodestuff.values()
    if context==first: 
        return second
    else:
        return first

def manage_addLinkManager(context, id="ZenLinkManager"):
    """ Make a LinkManager """
    mgr = LinkManager(id)
    context._setObject(mgr.id, mgr)
    mgr = context._getOb(id)
    _create_catalogs(mgr)


def _create_legacy_catalog_adapter(mgr, catalog_name):
    from Products.Zuul.catalog.legacy import LegacyCatalogAdapter
    if hasattr(mgr, catalog_name):
        mgr._delObject(catalog_name)
    setattr(mgr, catalog_name, LegacyCatalogAdapter(mgr.dmd, catalog_name))


def _create_catalogs(mgr):
    _create_legacy_catalog_adapter(mgr, 'layer2_catalog')
    _create_legacy_catalog_adapter(mgr, 'layer3_catalog')


class Layer3Link(object):
    """
    Provides an API for navigating paired groups of brains.
    """
    def __init__(self, dmd, twokeydict):
        a, b = twokeydict.items()
        aid, self.abrains = a
        bid, self.bbrains = b
        self.a = dmd.unrestrictedTraverse(aid)
        self.b = dmd.unrestrictedTraverse(bid)
        self.zep = getFacade('zep', dmd)
        self.idmgr = Manager(dmd)

    def _getComponentUuid(self, devuuid, compid):
        try:
            dev = self.idmgr.getElementByUuid(devuuid)
            compuuid = self.idmgr.getElementUuidById(dev, Device, compid)
            return compuuid
        except Exception:
            return None

    def getStatus(self):
        brains = self.abrains + self.bbrains

        # lookup all device uuids, make sure at least one exists
        devUuids = [self.idmgr.findDeviceUuid(a.deviceId.split("/")[-1], None) for a in brains if a.deviceId]
        validDevUuids = filter(None, devUuids)
        if not validDevUuids:
            return SEVERITY_CLEAR

        # if there is any open /Status/Ping event on any device, return CRITICAL severity
        statusPingFilter = self.zep.createEventFilter(
            tags = validDevUuids,
            event_class = '/Status/Ping/',
            status = (STATUS_NEW, STATUS_ACKNOWLEDGED),
            severity = (SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL)
        )
        maxpingrec = self.zep.getEventSummaries(0, filter=statusPingFilter, sort=(('count','desc'),), limit=1)
        if maxpingrec and maxpingrec['total'] > 0:
            return SEVERITY_CRITICAL

        # no /Status/Ping events found, just return worst severity of all events on all interface components
        devCompPairs = zip(devUuids, (a.interfaceId for a in brains))
        compUuids = (self._getComponentUuid(devuuid, compid)
                        for devuuid, compid in devCompPairs
                        if devuuid is not None)
        components = filter(None, compUuids)
        if components:
            sev = self.zep.getWorstSeverity(components)
            return sev

        return SEVERITY_CLEAR

    def getAddresses(self):
        return (self.a.address, self.b.address)

    def getUids(self):
        return ("/".join(self.a.getPhysicalPath()), "/".join(self.b.getPhysicalPath()))

class DeviceNetworksCache(object):
    """
    Data structure used to store the networks devices belong to.
        OOBTree
            Key:    Device.id
            Value:  OOBtree
                        Key:    Network
                        Value:  number of ip addresses that belong to that network
    """
    def __init__(self):
        self.cache = OOBTree()

    def add_device_network(self, device_id, network_id):
        """
        device_id = Device.getId()
        network_id = IpNetwork.getPrimaryUrlPath()
        """
        device_dict = self.cache.get(device_id)
        if device_dict is None:
            device_dict = OOBTree()
            self.cache[device_id] = device_dict
        network_value = device_dict.get(network_id, 0) + 1
        device_dict[network_id] = network_value

    def remove_device_network(self, device_id, network_id):
        """
        device_id = Device.getId()
        network_id = IpNetwork.getPrimaryUrlPath()
        """
        device_dict = self.cache.get(device_id)
        if device_dict:
            network_value = device_dict.get(network_id, 0) - 1
            if device_dict.has_key(network_id):
                if network_value > 0:
                    device_dict[network_id] = network_value
                else:
                    del device_dict[network_id]

    def remove_device(self, device_id):
        if self.cache.get(device_id):
            del self.cache[device_id]

    def get_device_networks(self, device_id):
        nets = set()

        if self.cache.get(device_id):
            nets = set(self.cache.get(device_id).keys())

        return nets

    def __str__(self):
        to_str = ""
        for dev, nets in self.cache.iteritems():
            to_str = to_str + "{0} => {1}\n".format(dev, len(nets.keys()))
            for net in nets.keys():
                to_str = to_str + "\t{0}\n".format(net)
        return to_str

class LinkManager(Folder):
    """ 
    A tool that keeps track of OSI layer links between objects.
    """
    def __init__(self, id, *args, **kwargs):
        Folder.__init__(self, id, *args, **kwargs)
        self.id = id
        self.networks_per_device_cache = DeviceNetworksCache()

    def _getCatalog(self, layer=3):
        try: 
            return getToolByName(self, 'layer%d_catalog' % layer)
        except AttributeError:
            return None

    def _get_brains(self, layer, attr, value):
        """
        hack to make getLinkedNodes's awful code work with as little changes as possible
        """
        model_catalog = IModelCatalogTool(self.dmd)
        query = {}
        if layer == 3:
            model_catalog = model_catalog.layer3
            meta_type = "IpAddress"
            query["deviceId"] = "*"  # We only are interested in assigned ips
        else:
            model_catalog = model_catalog.layer2
            meta_type = "IpInterface"
        query["meta_type"] = meta_type
        if isinstance(value, basestring):
            value = "*{0}".format(value)
        query[attr] = value
        search_results = model_catalog.search(query=query)
        return [ brain for brain in search_results.results ]

    def getLinkedNodes(self, meta_type, ids, layer=3, visited=None):
        col = NODE_IDS['layer_%d' % layer][meta_type]
        nextcol = _getComplement(col, layer)
        brains = self._get_brains(layer, col, ids)
        gen1ids = set(getattr(brain, nextcol) for brain in brains)
        if visited:
            gen1ids = gen1ids - visited # Don't go places we've been!
        gen2 = self._get_brains(layer, nextcol, list(gen1ids))
        return gen2, gen1ids

    def _get_devices_under_path(self, path):
        """ Returnd device's brains """
        model_catalog = IModelCatalogTool(self.dmd.Devices)
        query = {}
        query["objectImplements"] = "Products.ZenModel.Device.Device"
        query["path"] = "{0}".format(path)
        fields = ["id", "path"]
        result = model_catalog.search(query=query, fields=fields)
        return result.results

    # Deprecated. Left for testing purposes to compare perf and results with the new version
    def getChildLinks_old(self, organizer):
        result = {}
        locs = organizer.children()
        locpaths = sorted(('/'.join(loc.getPrimaryPath()) for loc in locs), reverse=True)
        path = '/'.join(organizer.getPhysicalPath())
        subdevs = self._get_devices_under_path(path)
        subids = dict((x.uid, x.path) for x in subdevs)

        def _whichorg(brain):
            for path in locpaths:
                _matchpath = lambda x: x.startswith(path)
                brainpath = subids.get(brain.deviceId, [])
                if any(ifilter(_matchpath, brainpath)):
                    return path
            return '__outside'
            
        def _whichnet(brain):
            return brain.networkId

        def _whichdev(brain):
            return brain.deviceId

        links, nets = self.getLinkedNodes('Device', subids.keys())
        links = map(aq_base, links) # For comparison, can't be ImplicitAcq

        _drawMapLinks = lambda x: \
            getattr(self.dmd.unrestrictedTraverse(x), 'zDrawMapLinks', True)

        # Organize the brains by Location and Network
        byloc = {}
        bynet = defaultdict(list)
        for link in links:
            dev = _whichdev(link)
            org = _whichorg(link)
            if dev and org != '__outside':
                byloc[dev] = org

            net = _whichnet(link)
            if _drawMapLinks(net):
                bynet[net].append(link)


        # Build the links (if found)
        linkobs = []
        for devs in bynet.itervalues():
            results = defaultdict(list)
            for d in devs:
                deviceId = d.deviceId
                loc = byloc.get(deviceId)
                if deviceId and loc:
                    results[loc].append(d)
            if len(results) >= 2:
                links = combinations(results.iteritems(), 2)
                linkobs.extend(Layer3Link(self.dmd, dict(l)) for l in links)
        return dumps([(x.getUids(), x.getStatus()) for x in linkobs])

    def getChildLinks(self, organizer):
        """
        Find networks that are in more than one location,
        build links between connected locations and
        get the link status
        """

        root_location_path_tuple = organizer.getPhysicalPath()
        root_location_path = '/'.join(root_location_path_tuple)

        locations = {}   # data structure to find to what top level location a device belongs to
        for loc in organizer.children():
            path_tuple = loc.getPrimaryPath()
            path_key = path_tuple[len(root_location_path_tuple)]
            locations[path_key] = path_tuple

        devices_per_location = defaultdict(set)   # { location: set( device_id ) }
        locations_per_network = defaultdict(set)  # { network:  set( location ) }

        devices_search = self._get_devices_under_path(root_location_path)

        for device_result in devices_search:
            device_id = device_result.id
            # get the the parent location the device belongs to
            device_location_full_path = next(ifilter(lambda x: 'Locations' in x, device_result.path))
            device_location_full_path_tuple = device_location_full_path.split('/')
            location_search_key = device_location_full_path_tuple[len(root_location_path_tuple)]
            device_parent_location = locations.get(location_search_key)
            if device_parent_location:
                device_location_path = '/'.join(device_parent_location)
                devices_per_location[device_location_path].add( device_id )
                device_networks = self.get_device_networks_from_cache(device_id)
                for net in device_networks:
                    locations_per_network[net].add(device_location_path)

        # At this point, any net in locations_per_network with more that one location is a link
        # if the net's zDrawMapLinks property is true
        linkobs = []
        linked_locations = defaultdict(set)  # { network: set( location ) }
        cat = IModelCatalogTool(self.dmd).layer3
        for net, locs in locations_per_network.iteritems():
            if len(locs) > 1:
                draw_maps = False
                try:
                    draw_maps = getattr(self.dmd.unrestrictedTraverse(net), 'zDrawMapLinks', True)
                except KeyError:
                    pass
                if not draw_maps:
                    continue
                results = defaultdict(list)
                layer3_brains = set(cat(query=Eq('networkId', net)))
                net_locations = defaultdict(list) # { location : l3 brains } for current net
                for loc in locs:
                    # get l3 brains that belong to net and whose device is in devices_per_location[location]
                    location_devices = devices_per_location[loc]
                    location_brains = set( [ b for b in layer3_brains if b.deviceId and b.deviceId.split("/")[-1] in location_devices ] )
                    layer3_brains = layer3_brains - location_brains
                    net_locations[loc] = list(location_brains)

                links = combinations(net_locations.iteritems(), 2)
                linkobs.extend(Layer3Link(self.dmd, dict(l)) for l in links)
        return dumps([(x.getUids(), x.getStatus()) for x in linkobs])

    def getChildLinks_recursive(self, context):
        """ Returns all links under a given Organizer, aggregated """
        result = set()
        severities = {}
        links = self.getNetworkLinks(context)
        for x in links:
            geomapdata = x.getGeomapData(context)
            severities[geomapdata] = max(
                x.getStatus(),
                severities.get(geomapdata, 0)
            ) 
            result.add(geomapdata)
        addresses = [x for x in list(result) if x]
        severities = [severities[x] for x in addresses]
        return map(list, zip(map(list, addresses), severities))

    def getNetworkLinks(self, context):
        """
        An alternate way to get links under an Organizer.
        """
        result = set()
        networks = filter(lambda x:x.zDrawMapLinks, 
                          self.dmd.Networks.getSubNetworks())
        siblings = [x.getPrimaryId() for x in context.children()]
        for net in networks:
            locdict = {}
            def addToDict(iface):
                loc = iface.device().location()
                if not loc: return
                here = loc.getPrimaryId()
                matched = False
                for sib in siblings:
                    if here.startswith(sib):
                        locdict.setdefault(sib, []).append(iface)
                        matched = True
                        break
                if not matched: 
                    locdict.setdefault(here, []).append(iface)
            for ip in net.ipaddresses.objectValuesGen():
                iface = ip.interface()
                if iface: addToDict(iface)
            if len(locdict)<=1: continue
            locgroups = locdict.values()
            while locgroups:
                lg = locgroups.pop()
                targets = []
                for g in locgroups: targets.extend(g)
                for l in lg:
                    for t in targets:
                        n = NetworkLink()
                        n.setEndpoints(l, t)
                        result.add(n)
        return result

    # Methods to access self.networks_per_device_cache
    #
    def add_device_network_to_cache(self, device_id, network_id):
        if hasattr(self, "networks_per_device_cache"):
            self.networks_per_device_cache.add_device_network(device_id, network_id)

    def remove_device_network_from_cache(self, device_id, network_id):
        if hasattr(self, "networks_per_device_cache"):
            self.networks_per_device_cache.remove_device_network(device_id, network_id)

    def remove_device_from_cache(self, device_id):
        if hasattr(self, "networks_per_device_cache"):
            self.networks_per_device_cache.remove_device(device_id)

    def get_device_networks_from_cache(self, device_id):
        if hasattr(self, "networks_per_device_cache"):
            return self.networks_per_device_cache.get_device_networks(device_id)
        else:
            return set()

InitializeClass(LinkManager)
