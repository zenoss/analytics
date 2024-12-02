##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IInfo, IFacade, ITreeNode


class IDeviceOrganizerNode(ITreeNode):
    """
    Marker interface for device organizer nodes in a tree.
    """

class IDevice(Interface):
    """
    Marker interface for Device.
    """

class IDeviceOrganizerInfo(IInfo):
    """
    DeviceClass info
    """
    events = Attribute('A list of (severity, count) tuples for the three most'
                       ' severe event severities')

class IDeviceCollectorChangeEvent(Interface):
    """
    Device's collector change event
    """
    context = Attribute("Reference to contextual database object.")
    collector = Attribute("The collector the devices are moving to")
    movedDevices = Attribute("Device moves (dict of device 'id' and 'fromCollector' references)")


class IDeviceInfo(IInfo):
    """
    Device info
    """
    device = Attribute('The ID of the device')
    ipAddress = Attribute('The management IP address')
    ipAddressString = Attribute('A string representation of the management IP address')
    productionState = Attribute('The production state of the device')
    events = Attribute('A list of (severity, count) tuples for the three most'
                       ' severe event severities')
    availability = Attribute('The availability percentage')

    def getDevice():
        """
        Returns the device attribute. Handy as a key when sorting a list of
        IDeviceInfos.
        """

class IDeviceFacade(IFacade):
    """
    Responsible for navigating the Device Class hierarchy and managing devices
    and components.
    """
    def getComponents(uid, types, meta_type):
        """
        Get C{IInfo} objects representing all components of type C{types} or
        C{meta_type} under the path represented by C{uid}.

        @param uid: The primary path of the root under which to search for components
        @type uid: str
        @param types: One or more dotted names matching components must provide
        @type types: str, list, tuple
        @param meta_type: One or more meta_types matching components must be
        @type meta_type: str, list, tuple
        @return: Matching component objects adapted to C{IInfo}
        @rtype: iterable
        """
    def getComponentTree(uid, types, meta_type):
        """
        Get a list of dictionaries representing the meta_types of components
        under the path identified by C{uid}, the number of component instances
        in each, and the aggregated maximum event severity.

        @param uid: The primary path of the root under which to search for components
        @type uid: str
        @param types: One or more dotted names matching components must provide
        @type types: str, list, tuple
        @param meta_type: One or more meta_types matching components must be
        @type meta_type: str, list, tuple
        @return: Dictionaries with keys [type, count, severity]
        @rtype: list
        """
    def deleteDevices(uids):
        """
        Delete devices from the system.

        @param uids: The primary paths of the devices to delete
        @type uids: list
        @rtype: void
        """
    def removeDevices(uids, organizer):
        """
        Remove devices represented by C{uids} from C{organizer}.

        @param uids: The primary paths of the devices to remove
        @type uids: list
        @param organizer: The primary path of the L{DeviceOrganizer} from which
        to remove the devices
        @type organizer: str
        @rtype: void
        """
    def getUserCommands(uid):
        """
        Get C{UserCommand} objects defined on the object represented by C{uid}.
        If not defined on C{uid}, commands will be acquired.

        @param uid: The primary path of the object to get commands for
        @type uid: str
        @return: C{UserCommand}s
        @rtype: list
        """
    def setLockState(uids, deletion=False, updates=False, sendEvent=False):
        """
        Set the locking for the objects represented by C{uids}.

        @param uids: The primary paths of the objects whose locking state
        should be modified
        @type uids: list, tuple
        @param deletion: Whether to lock objects from deletion during modeling
        @type deletion: bool
        @param updates: Whether to lock objects from updates during modeling
        @type updates: bool
        @param sendEvent: Whether to generate an event when an action is
        blocked by locking for these objects
        @type sendEvent: bool
        @return: void
        """
    def resetCommunityString(uid):
        """
        Clear the SNMP community string defined on the device represented by
        C{uid} and reset its value by checking those defined by
        C{zSnmpCommunities} against the device.

        @param uid: The primary path of the object
        @type uid: str
        @rtype: void
        """
    def moveDevices(uids, target):
        """
        Move devices represented by C{uids} to the organizer represented by
        C{target}. If C{target} is a System or DeviceGroup, the devices will be
        added to C{target}. If C{target} is a DeviceClass or Location, the devices will be
        removed from their current organizer and moved to C{target}.

        @param uids: The primary paths of the objects to move
        @type uids: list, tuple
        @param uids: The primary path of the organizer to move devices to
        @type uids: str
        @rtype: void
        """

    def addDevice(deviceName, deviceClass, title=None, snmpCommunity="",
                  snmpPort=161, model=False, collector='localhost',
                  rackSlot=0, productionState=1000, comments="",
                  hwManufacturer="", hwProductName="", osManufacturer="",
                  osProductName="", priority = 3, tag="", serialNumber=""):
        """
        Add a device using the deviceName and deviceClass

        @param deviceName: host name or IP of the device
        @type deviceName: string
        @param deviceClass: path for device creation, e.g. /Server/Linux
        @type deviceClass: string
        @param title: title to be displayed for device if if different than
                    deviceName
        @type title: string
        @param snmpCommunity: snmp community to use
        @type snmpCommunity: string
        @param snmpPort: port to use for snmp
        @type snmpPort: int
        @param model: should the device be modeled; default False
        @type model: boolean
        @param collector: name of the collector for the device
        @type collector: string
        @rtype: IJobStatus

        """

    def getUnboundTemplates(uid):
        """
        Fetch the monitoring templates that are not bound to the DeviceClass
        or Device uniquely identified by the uid parameter. These monitoring
        templates are defined directly on the object or are available in the
        object's acqisition chain. They are considered unbound because their
        IDs are not listed in the zDeviceTemplates property and therefore are
        not used by the monitoring daemons.
        """

    def getBoundTemplates(uid):
        """
        Fetch the monitoring templates that are bound to the DeviceClass or
        Device uniquely identified by the uid parameter. These monitoring
        templates are defined directly on the object or are available in the
        object's acqisition chain. They are considered bound because their
        IDs are listed in the zDeviceTemplates property and therefore are
        used by the monitoring daemons.
        """

    def setBoundTemplates(self, uid, templateIds):
        """
        Set the zDeviceTemplates property on the DeviceClass or Device
        uniquely identified by the uid parameter to the value of the
        templateIds parameter.
        """

    def resetBoundTemplates(self, uid):
        """
        Remove templates bound to the Device identified by C{uid}.

        @param uid: The primary path of the object
        @type uid: str
        @rtype: void
        """
