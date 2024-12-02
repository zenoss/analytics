##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenModel.Link import ILink


# Validation for Device subtypes and IpNetwork subtypes.  Cannot import these 
# class types directly, because this module is inherited by those classes
# (Fixes for ZEN-4657)

def isDeviceInstance(ob):
    from Products.ZenModel.Device import Device
    return isinstance(ob, Device)

def isIpNetworkInstance(ob):
    from Products.ZenModel.IpNetwork import IpNetwork
    return isinstance(ob, IpNetwork)

def _fromDeviceToNetworks(dev):
    for iface in dev.os.interfaces():
        for ip in iface.ipaddresses():
            net = ip.network()
            if net is None or net.netmask == 32:
                continue
            else:
                yield net

def _fromNetworkToDevices(net, organizer):
    from Products.Zuul.catalog.global_catalog import IIndexableWrapper
    for ip in net.ipaddresses():
        dev = ip.device()
        if dev is None:
            continue
        paths = map('/'.join, IIndexableWrapper(dev).path())
        for path in paths:
            if path.startswith(organizer) or path.startswith('/zport/dmd/Devices/Network/Router'):
                yield dev
                break

def _get_related(node, filter='/'):
    if isIpNetworkInstance(node):
        children = _fromNetworkToDevices(node, filter)
    elif isDeviceInstance(node):
        children = _fromDeviceToNetworks(node)
    else:
        raise NotImplementedError
    return children

def _sortedpair(x,y):
    l = [x,y]
    cmpf = lambda x,y:int(isDeviceInstance(x))-int(isDeviceInstance(y))
    l.sort(cmpf)
    return tuple(l)

def _get_connections(rootnode, depth=1, pairs=None, filter='/'):
    """ Depth-first search of the network tree emanating from
        rootnode, returning (network, device) edges.
    """
    if not pairs:
        pairs = []
    if depth:
        for node in _get_related(rootnode, filter):
            sorted = _sortedpair(rootnode, node)
            pair = [x.id for x in sorted]
            if pair not in pairs:
                pairs.append(pair)
                yield sorted
                for childnode in _get_related(node, filter):
                    for n in _get_connections(
                        childnode, depth-1, pairs, filter):
                        yield n

def get_edges(rootnode, depth=1, withIcons=False, filter='/'):
    """ Returns some edges """
    depth = int(depth)
    g = _get_connections(rootnode, depth, [], filter)
    def getColor(node):
        if isIpNetworkInstance(node):
            return '0xffffff'
        summary = node.getEventSummary()
        colors = '0xff0000 0xff8c00 0xffd700 0x00ff00 0x00ff00'.split()
        color = '0x00ff00'
        for i in range(5):
            if summary[i][2]>0:
                color = colors[i]
                break
        return color
    for nodea, nodeb in g:
        if withIcons:
            yield ((nodea.titleOrId(), nodea.getIconPath(), getColor(nodea), nodea.getId()),
                   (nodeb.titleOrId(), nodeb.getIconPath(), getColor(nodeb), nodeb.getId()))
        else:
            yield (nodea.titleOrId(), nodeb.titleOrId())

def getDeviceNetworkLinks(rootdevice):
    """ Returns network links to other devices """
    visited = []
    ifaces = rootdevice.os.interfaces()
    ifaceids = [x.getPrimaryId() for x in ifaces]
    for iface in ifaces:
        for ip in iface.ipaddresses.objectValuesGen():
            for ipsib in ip.network().ipaddresses.objectValuesGen():
                ifacesib = ipsib.interface()
                if ifacesib is None: continue
                if (ifacesib.getPrimaryId() in visited or
                    ifacesib.getPrimaryId() in ifaceids):
                    continue
                visited.append(ifacesib.getPrimaryId())
                link = NetworkLink()
                link.setEndpoints(iface, ifacesib)
                yield link



class NetworkLink(ILink):
    """ Represents a link between two IpInterfaces
        related by network connectivity.
        Not a persistent object, so not managed
        by a LinkManager.
        Implements Products.ZenModel.Link.ILink.
    """

    OSI_layer = '3'
    pointa = None
    pointb = None

    def __hash__(self):
        eps = sorted(x.id for x in self.getEndpoints())
        return hash(':'.join(eps))

    def setEndpoints(self, pointa, pointb):
        self.pointa = pointa
        self.pointb = pointb
        self.endpoints = (pointa, pointb)

    def getEndpoints(self):
        return self.endpoints

    def getStatus(self):
        eps = self.endpoints
        if max(ep.getPingStatus() for ep in eps) > 0:
            return 5
        zem = eps[0].dmd.ZenEventManager
        return max(map(zem.getMaxSeverity,eps))

    def getEndpointNames(self):
        return (self.pointa.id, self.pointb.id)

    def getOtherEndpoint(self, endpoint):
        if endpoint==self.pointa: return self.pointb
        elif endpoint==self.pointb: return self.pointa
        else: return None

    def getDataForJSON(self):
        # Eventually will return data for serialization
        import json
        return json.dumps([
            self.id,
            self.getEndpointNames()[0],
            self.getEndpointNames()[1],
            self.OSI_layer,
            self.link_type,
            self.entry_type,
            self.id
        ])

    def getGeomapData(self, context, full=False):
        """ Return the addresses of the endpoints
            aggregated for the generation of the context
        """
        dmd = context.dmd
        generation = len(context.getPrimaryPath())+1
        def getancestoraddress(endpoint):
            loc = endpoint.device().location()
            if loc is None: return
            path = loc.getPrimaryPath()
            path = '/'.join(path[:generation])
            ancestor = dmd.getObjByPath(path)
            if full:
                return ancestor.getGeomapData()
            else:
                return ancestor.address
        result = map(getancestoraddress, self.endpoints)
        result = filter(lambda x:x, result)
        if len(result) < 2: return None
        if result[0]==result[1]: return None
        result.sort()
        return tuple(result)
