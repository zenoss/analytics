##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.component import adapts
from zope.interface import implements
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenUtils import IpUtil
from Products.Zuul.tree import TreeNode
from Products.Zuul.interfaces import IDeviceOrganizerNode
from Products.Zuul.interfaces import IDeviceOrganizerInfo
from Products.Zuul.interfaces import IDeviceInfo, IDevice, IInfo
from Products.Zuul.infos import (
    InfoBase,
    HasEventsInfoMixin,
    ProxyProperty,
    LockableMixin
)
from Products.Zuul import getFacade, info
from Products.Zuul.marshalling import TreeNodeMarshaller
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_INFO, SEVERITY_DEBUG
from Products.ZenModel.ZenossSecurity import ZEN_VIEW
from Products.ZCatalog.interfaces import ICatalogBrain

from Products.Zuul.infos.catalog_tree_builder import ModelCatalogTreeBuilder


ORGTYPES = {
    'Devices': 'DeviceClass',
    'Systems': 'Systems',
    'Locations': 'Location',
    'Groups': 'DeviceGroups'
}


class DeviceOrganizerNode(TreeNode):
    implements(IDeviceOrganizerNode)
    adapts(DeviceOrganizer)

    def __init__(self, ob, root=None, parent=None):
        super(DeviceOrganizerNode, self).__init__(ob, root, parent)
        obj = self._get_object()
        # Calling hasNoGlobalRoles() is expensive in the context of a large
        # organizer tree. Use the same value from the root node if it is
        # available (it doesn't change based on the context of the organizer).
        if root:
            self.hasNoGlobalRoles = root.hasNoGlobalRoles
        else:
            self.hasNoGlobalRoles = obj.dmd.ZenUsers.getUserSettings().hasNoGlobalRoles()

    @property
    def viewable_objects_uid(self):
        """
        This is only for users with no global roles. Returns the node
        uids that should be displayed for the current user
        """
        attr_name = '_viewable_objects_uid'
        viewable_uids = getattr(self._root, attr_name, None)
        if viewable_uids is None:
            allowed_uids = set()
            root = self._root._get_object()
            root_uid_tuple = root.getPrimaryPath()
            root_uid = "/".join(root_uid_tuple)
            user = root.dmd.ZenUsers.getUserSettings()
            for adminObj in user.getAllAdminRoles():
                uid_tuple = adminObj.managedObject().getPrimaryPath()
                uid = "/".join(uid_tuple)
                if uid.startswith(root_uid):
                    # We are only interested in the objects that are under
                    # the tree we are building
                    allowed_uids.add(uid_tuple)
            viewable_uids = set()
            # See Trac #2725, unrestricted users need to see the nodes
            # they don't have permission to view if they do have permissions
            # on any of the child nodes.
            root_depth = len(root_uid_tuple)
            for uid_tuple in allowed_uids:
                for i in range(root_depth, len(uid_tuple)):
                    viewable_uids.add("/".join(uid_tuple[:i + 1]))
            if viewable_uids:
                viewable_uids.add(root_uid)  # add the root
            setattr(self._root, attr_name, viewable_uids)
        return viewable_uids

    @property
    def tree_from_catalog(self):
        attr_name = '_tree_from_catalog'
        tree = getattr(self._root, attr_name, None)
        if tree is None:
            node_type = "Products.ZenModel.DeviceOrganizer.DeviceOrganizer"
            leaf_type = "Products.ZenModel.Device.Device"
            facet_field = "deviceOrganizers"
            load_leaves = False
            splitted_path = self._root._get_object().getPrimaryPath()
            if splitted_path[3] in ["Systems", "Groups"]:
                # Bc a device can belong to more than one system or group,
                # we need to load all devices in order to retrieve the total
                # count of unique devices
                load_leaves = True
            tree = ModelCatalogTreeBuilder(
                self._root._get_object(), node_type, leaf_type,
                load_leaves=load_leaves, facet_field=facet_field
            )
            setattr(self._root, attr_name, tree)
        return tree

    @property
    def load_tree_from_catalog(self):
        attr_name = '_load_tree_from_catalog'
        use_it = getattr(self._root, attr_name, None)
        if use_it is None:
            root = self._root._get_object()
            use_it = root.dmd.UserInterfaceSettings.getInterfaceSettings().get(
                'loadDeviceTreeFromCatalog'
            )
            setattr(self._root, attr_name, use_it)
        return use_it

    @property
    def children(self):
        if getattr(self, '_cached_children', None) is None:
            self._cached_children = map(
                lambda x: DeviceOrganizerNode(x, self._root, self),
                self._get_children()
            )
        return self._cached_children

    def _get_children(self):
        obj = self._get_object()
        if self.load_tree_from_catalog:
            node_path = "/".join(obj.getPrimaryPath())
            children = self.tree_from_catalog.get_children(node_path)
        else:
            if self.hasNoGlobalRoles:
                # if user has no global roles we cant use children bc it
                # returns organizers for which the user has perms.
                # We need all of them in case the user has access to devices
                # in organizers for which the user does not have permissions
                children = obj.objectValues(spec=obj.meta_type)
            else:
                children = obj.children()
            children = sorted(children, key=lambda org: org.titleOrId())

        if self.hasNoGlobalRoles:  # filter children
            children = filter(self._nonGlobalRole_child_filter, children)
        return children

    def _nonGlobalRole_child_filter(self, child):
        """
        When user does not have global perms, filter children
        based on if the user has permissions for the especific organizer
        or a device in the organizer
        """
        include = False
        obj = self._get_object()
        if ICatalogBrain.providedBy(child):
            child = child.getObject()
        child_uid = "/".join(child.getPrimaryPath())

        if obj.checkRemotePerm(ZEN_VIEW, child) or \
           child_uid in self.viewable_objects_uid:
            include = True

        return include

    def _count_devices(self):
        if getattr(self, '_cached_count', None) is None:
            if self.load_tree_from_catalog:
                obj = self._get_object()
                node_path = "/".join(obj.getPrimaryPath())
                count = self.tree_from_catalog.get_leaf_count(node_path)
            else:
                # De-duplicate so we don't repeatedly count the same device in
                # multiple sub-organizers.
                count = len(self._unique_keys())
            self._cached_count = count
        return self._cached_count

    def _unique_keys(self):
        unique_keys = set()
        for child in self.children:
            unique_keys.update(child._unique_keys())
        for device in self._get_object().devices():
            unique_keys.add(device.id)
        return unique_keys

    @property
    def text(self):
        numInstances = None
        # Only show count if user has global permissions
        if not self.hasNoGlobalRoles:
            numInstances = self._count_devices()
        text = super(DeviceOrganizerNode, self).text
        return {
            'text': text,
            'count': numInstances,
            'description': 'devices'
        }

    @property
    def zPythonClass(self):
        return self._get_object().getZ('zPythonClass')

    # All nodes are potentially branches, just some have no children
    leaf = False


class DeviceOrganizerTreeNodeMarshaller(TreeNodeMarshaller):
    """
    Doesn't get iconCls for each individually. Loads up max sevs for all nodes
    first, then each node can look up its severity from that single query.
    """

    def __init__(self, root):
        super(DeviceOrganizerTreeNodeMarshaller, self).__init__(root)
        self._severities = {}
        self._eventFacade = getFacade('zep')
        self._uuids = {}
        self.showSeverityIcons = root._shouldShowSeverityIcons()

    def _getNodeUuid(self, node):
        if node not in self._uuids:
            self._uuids[node] = node.uuid

        return self._uuids[node]

    def _getUuids(self, node):
        uuids = set([self._getNodeUuid(node)])
        if not node.leaf:
            for child in node.children:
                uuids.update(self._getUuids(child))
        return uuids

    @property
    def _allSeverities(self):
        if not self._severities:
            # Get UUIDs for all items in the tree
            uuids = self._getUuids(self.root)
            events = self._eventFacade.getWorstSeverity(
                uuids, ignore=(SEVERITY_INFO, SEVERITY_DEBUG)
            )
            self._severities = {
                uuid: self._eventFacade.getSeverityName(severity).lower()
                for (uuid, severity)
                in events.iteritems()
            }

        return self._severities

    def _marshalNode(self, keys, node, iconCls=False):
        obj = self.getValues(keys, node)
        if node.leaf:
            obj['leaf'] = True

        if 'uuid' in keys:
            obj['uuid'] = self._getNodeUuid(node)

        if iconCls and self.showSeverityIcons:
            severity = self._allSeverities.get(
                self._getNodeUuid(node), 'clear'
            )
            obj['iconCls'] = node.getIconCls(severity)

        obj['children'] = []
        for childNode in node.children:
            obj['children'].append(
                self._marshalNode(keys, childNode, iconCls=iconCls)
            )
        return obj

    def marshal(self, keys=None, node=None):
        # Remove iconCls key so we don't get its intrinsic value,
        # instead we want to get it in batches
        keys = keys or self.getKeys()
        iconCls = False
        if 'iconCls' in keys:
            iconCls = True
            keys.remove('iconCls')
        return self._marshalNode(keys, node or self.root, iconCls=iconCls)


class DeviceInfo(InfoBase, HasEventsInfoMixin, LockableMixin):
    implements(IDeviceInfo)
    adapts(IDevice)

    @property
    def device(self):
        return self._object.id

    def getDevice(self):
        return self.device

    def getIpAddress(self):
        if self._object.manageIp:
            return IpUtil.ipToDecimal(self._object.manageIp)

    def setIpAddress(self, ip=None):
        msg = self._object.setManageIp(ip)
        if msg:
            raise Exception(msg)

    ipAddress = property(getIpAddress, setIpAddress)

    @property
    def ipAddressString(self):
        manageIp = self._object.manageIp
        if manageIp:
            if "%" in manageIp:
                address, interface = manageIp.split("%")
            else:
                address = manageIp
                interface = None
            addr_part = IpUtil.IPAddress(address)
            if interface is None:
                addr_string = "%s" % addr_part
            else:
                addr_string = "%s%%%s" % (addr_part, interface)
        else:
            addr_string = None
        return addr_string

    @property
    def productionStateLabel(self):
        return self._object.convertProdState(self._object.getProductionState())

    def getProductionState(self):
        return self._object.getProductionState()

    def setProductionState(self, prodState):
        # prodState gets cast to an integer in the device facade.
        return getFacade('device').setProductionState(self.uid, prodState)

    productionState = property(getProductionState, setProductionState)

    def getPriority(self):
        return self._object.priority

    def setPriority(self, priority):
        # priority is cast to an integer in Device.setPriority
        self._object.setPriority(priority)

    priority = property(getPriority, setPriority)

    @property
    def priorityLabel(self):
        return self._object.convertPriority(self._object.priority)

    def getCollectorName(self):
        return self._object.getPerformanceServerName()

    def setCollector(self, collector):
        self._object.setPerformanceMonitor(collector)

    collector = property(getCollectorName, setCollector)

    def availability(self):
        return self._object.availability().availability

    @property
    def status(self):
        status = self._object.getDeviceStatus()
        return None if status is None else status < 1

    @property
    def deviceClass(self):
        return info(self._object.deviceClass())

    def _organizerInfo(self, objs):
        result = []
        for obj in objs:
            info = IInfo(obj)
            result.append({
                'name': info.name,
                'uid': info.uid,
                'uuid': info.uuid,
                'path': info.path
            })
        return result

    @property
    def groups(self):
        return self._organizerInfo(self._object.groups())

    @property
    def systems(self):
        return self._organizerInfo(self._object.systems())

    @property
    def location(self):
        loc = self._object.location()
        if loc:
            info = IInfo(loc)
            return dict(name=info.name, uid=info.uid, uuid=info.uuid)

    @property
    def uptime(self):
        return self._object.uptimeStr()

    @property
    def firstSeen(self):
        return self._object.createdTime.timeTime()

    @property
    def lastChanged(self):
        return self._object._lastChange

    @property
    def created_timestamp(self):
        return self._object.created_timestamp

    @property
    def lastCollected(self):
        if self._object._snmpLastCollection:
            return self._object._snmpLastCollection
        return "Not Modeled"

    def getComments(self):
        return self._object.comments

    def setComments(self, value):
        self._object.comments = value

    comments = property(getComments, setComments)

    @property
    def links(self):
        return self._object.getExpandedLinks()

    @property
    def locking(self):
        return {
            'updates': self._object.isLockedFromUpdates(),
            'deletion': self._object.isLockedFromDeletion(),
            'events': self._object.sendEventWhenBlocked()
        }

    def getTagNumber(self):
        return self._object.hw.tag

    def setTagNumber(self, value):
        self._object.hw.tag = value

    tagNumber = property(getTagNumber, setTagNumber)

    def getSerialNumber(self):
        return self._object.hw.serialNumber

    def setSerialNumber(self, value):
        self._object.hw.serialNumber = value

    serialNumber = property(getSerialNumber, setSerialNumber)

    @property
    def hwManufacturer(self):
        if self.hwModel is not None:
            return info(self.hwModel._object.manufacturer())

    @property
    def hwModel(self):
        if self._object.hw:
            return info(self._object.hw.productClass())

    @property
    def osManufacturer(self):
        if self.osModel is not None:
            return info(self.osModel._object.manufacturer())

    @property
    def osModel(self):
        if self._object.os:
            return info(self._object.os.productClass())

    @property
    def memory(self):
        return {
            'ram': self._object.hw.totalMemoryString(),
            'swap': self._object.os.totalSwapString()
        }

    def getRackSlot(self):
        return self._object.rackSlot

    def setRackSlot(self, value):
        self._object.rackSlot = value

    rackSlot = property(getRackSlot, setRackSlot)

    def getSnmpSysName(self):
        return self._object.snmpSysName

    def setSnmpSysName(self, value):
        self._object.snmpSysName = value

    snmpSysName = property(getSnmpSysName, setSnmpSysName)

    def getSnmpContact(self):
        return self._object.snmpContact

    def setSnmpContact(self, value):
        self._object.snmpContact = value

    snmpContact = property(getSnmpContact, setSnmpContact)

    def getSnmpLocation(self):
        return self._object.snmpLocation

    def setSnmpLocation(self, value):
        self._object.snmpLocation = value

    snmpLocation = property(getSnmpLocation, setSnmpLocation)

    def getSnmpAgent(self):
        return self._object.snmpAgent

    def setSnmpAgent(self, value):
        self._object.snmpAgent = value

    snmpAgent = property(getSnmpAgent, setSnmpAgent)

    snmpDescr = ProxyProperty('snmpDescr')

    @property
    def snmpCommunity(self):
        return self._object.getProperty('zSnmpCommunity')

    @property
    def snmpVersion(self):
        return self._object.getProperty('zSnmpVer')

    @property
    def icon(self):
        return self._object.getIconPath()

    @property
    def pythonClass(self):
        return self._object.__class__.__module__

    @property
    def sshLink(self):
        """
        Returns the "href" for connecting to this device. Assumes most
        devices can be connected to by ssh.
        """
        ipAddress = self.ipAddressString
        userName = self._object.getZ('zCommandUsername', 'root')
        if not ipAddress:
            return None
        # for empty strings
        if not userName:
            userName = "root"
        return "ssh://%s@%s" % (userName, ipAddress)

    @property
    def deviceConnectionInfo(self):
        connectionInfo = []
        zprops = self._object.deviceClass().primaryAq().getZ(
            'zCredentialsZProperties', []
        )
        if not zprops:
            return False
        for prop in zprops:
            if not self._object.zenPropIsPassword(prop):
                connectionInfo.append(
                    str(self._object.zenPropertyString(prop))
                )
        return " ".join(connectionInfo)

    @property
    def renameInProgress(self):
        return self._object.renameInProgress


class DeviceOrganizerInfo(InfoBase, HasEventsInfoMixin):
    implements(IDeviceOrganizerInfo)
    adapts(DeviceOrganizer)

    def getName(self):
        return self._object.getOrganizerName()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    @property
    def path(self):
        return self._object.getPrimaryDmdId()


def _removeZportDmd(path):
    if path.startswith('/zport/dmd'):
        path = path[10:]
    return path
