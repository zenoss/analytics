##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from zope.interface import Attribute, Interface
from Products.Zuul.interfaces import IInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class IComponent(Interface):
    """
    An IComponent is a device component (an instance of OSComponent or
    HWComponent). Examples of device components are OSProcesses, IPServices and
    WinServices.
    """
    def device():
        """
        The parent device of this component.
        """

class IComponentInfo(IInfo):
    """
    An info adapter that wraps a device component.  Examples of device
    components are OSProcesses, IPServices and WinServices.
    """
    device = Attribute("Parent Device")
    status = schema.TextLine(title=_t(u"Status"),
                             description=u"Are there any active status events"
                                         u" for this component?", group="Overview",
                             order=1,
                             readonly=True)
    deviceName = schema.TextLine(title=_t(u"Device"),
                                 description=u"Parent Device Name/Title",
                                 group="Overview",
                                 order=2,
                                 readonly=True)
    usesMonitorAttribute = Attribute("Should the user be able to set the monitor attribute")
    monitor = Attribute("Has monitoring been enabled on the component")
    monitored = Attribute(u"Is the component being monitored"
                            u" (depends on the monitor setting and other"
                            u" factors). Empty string if not applicable.")


class IIpInterfaceInfo(IComponentInfo):
    """
    Info adapter for IPInterface components.
    """
    interfaceName = schema.TextLine(
        title=_t(u"Interface Name"), group="Overview",
        order=1)

    description = schema.Text(
        title=_t(u"Description"), group="Overview",
        order=2)

    adminStatus = schema.TextLine(
        title=_t(u"Administrative Status"), group="Overview",
        readonly=True, order=3)

    operStatus = schema.TextLine(
        title=_t(u"Operational Status"), group="Overview",
        readonly=True, order=4)

    status = schema.TextLine(
        title=_t(u"Status"), group="Overview",
        description=u"Are there any active status events for this component?"
                    u" for this component?",
        readonly=True, order=5)

    ipAddress = schema.Entity(
        title=_t(u"IP Address (Primary)"), group="Overview",
        description=u"Primary IP address",
        order=6)

    ipAddresses = schema.List(
        title=_t(u'IP Addresses (All)'), group="Details",
        order=7)

    macaddress = schema.TextLine(
        title=_t(u"MAC Address"), group="Details",
        order=8)

    type = schema.TextLine(
        title=_t(u"Type"), group="Details",
        order=9)

    speed = schema.TextLine(
        title=_t(u"Speed"), group="Details", readonly=True,
        order=10)

    duplex = schema.TextLine(
        title=_t(u"Duplex Mode"), group="Details",
        readonly=True, order=11)

    mtu = schema.TextLine(
        title=_t(u"MTU"), group="Details",
        order=12)

    ifindex = schema.TextLine(
        title=_t(u"SNMP Index"), group="Details",
        order=13)


class IFileSystemInfo(IComponentInfo):
    """
    Info adapter for FileSystem components.
    """
    mount = schema.TextLine(title=_t(u"Mount Point"), group="Overview", order=-1)
    storageDevice = schema.TextLine(title=_t(u"Storage Device"), group="Details")
    type = schema.TextLine(title=_t(u"Type"), group="Details")
    blockSize = schema.Int(title=_t(u"Block Size"), group="Details")
    totalBlocks = Attribute("Total Blocks")
    totalBytes = schema.Int(title=_t(u"Total Bytes"), readonly=True,
                            group="Details")
    usedBytes = schema.Int(title=_t(u"Used Bytes"), readonly=True, group="Details")
    availableBytes = schema.Int(title=_t(u"Available Bytes"), readonly=True,
                                group="Details")
    capacityBytes = schema.Int(title=_t(u"Capacity Bytes"), readonly=True,
                               group="Details")
    totalFiles = schema.Int(title=_t(u"Total Files"), group="Details")
    availableFiles = schema.Int(title=_t(u"Available Files"), readonly=True,
                                group="Details")
    capacityFiles = schema.Int(title=_t(u"Capacity Files"), readonly=True,
                               group="Details")
    maxNameLength = schema.Int(title=_t(u"Maximum Name Length"), group="Details")


class IOSProcessInfo(IComponentInfo):
    """
    Info adapter for OSProcess components.
    """
    processClass = schema.Entity(title=_t(u"Process Class"), group="Overview",
                                 order=1)
    getMonitoredProcesses = schema.TextLine(title=u"Process(es) identified by the most recent model", group="Details", 
                                            readonly=True, order=-1) 
    processName = schema.TextLine(title=_t(u"Process Set Name"), group="Overview",
                                  readonly=True, order=-1)
    description = schema.Text(title=_t(u"Description"), group="Overview",
                              readonly=True, order=2)
    alertOnRestart = schema.Bool(title=_t(u"Alert on Restart"), group="Details",
                                 alwaysEditable=True)
    failSeverity = schema.Int(title=_t(u"Fail Severity"), xtype="severity",
                              group="Details", alwaysEditable=True)
    minProcessCount = schema.Int(title=u"Min Process Count",
                                 group="Details", alwaysEditable=True)
    maxProcessCount = schema.Int(title=u"Max Process Count",
                                 group="Details", alwaysEditable=True)
    minProcessMemory = schema.Int(title=u"Min Process Memory",
                                 group="Details", alwaysEditable=True)
    maxProcessMemory = schema.Int(title=u"Max Process Memory",
                                 group="Details", alwaysEditable=True)


class IWinServiceInfo(IComponentInfo):
    """
    Info adapter for WinService components.
    """
    serviceName = schema.Text(title=_t(u"Name"), group="Overview")
    serviceClass = schema.Entity(title=_t(u"Service Class"), group="Overview")
    caption = schema.TextLine(title=_t(u"Caption"), group="Overview")
    command = schema.TextLine(title=_t(u"Command"), group="Overview")
    failSeverity = schema.Int(title=_t(u"Fail Severity"), xtype="severity",
                              group="Details", alwaysEditable=True)
    serviceType = schema.TextLine(title=_t(u"Service Type"), group="Details")
    startMode = schema.TextLine(title=_t(u"Start Mode"), group="Details")
    startName = schema.TextLine(title=_t(u"Start Name"), group="Details")
    pathName = schema.TextLine(title=_t(u"Path Name"), group="Details")


class IIpServiceInfo(IComponentInfo):
    """
    Info adapter for IpService components
    """
    description = schema.Text(title=_t(u"Description"),
                              group="Overview")
    serviceClass = schema.Entity(title=_t(u"Service Class"), group="Overview")
    port = schema.Int(title=_t(u"Port"), group="Overview")
    protocol = schema.TextLine(title=_t(u"Protocol"), group="Details")
    ipaddresses = schema.List(title=_t(u"IP Addresses"), group="Details")
    manageIp = schema.TextLine(title=_t(u"Management IP Address"),
                               group="Overview", alwaysEditable=True,
                               xtype="ipaddressfield", vtype="ipaddress")
    discoveryAgent = schema.TextLine(title=_t(u"Discovery Agent"), group="Details")
    failSeverity = schema.Int(title=_t(u"Fail Severity"), xtype="severity",
                              group="Details", alwaysEditable=True)
    sendString = schema.Text(title=_t(u"Send String"), group="Details")
    expectRegex = schema.TextLine(title=_t(u"Expect Regex"), group="Details")



class IIpRouteEntryInfo(IComponentInfo):
    """
    Info adapter for IpRouteEntry components.
    """
    destination = schema.Entity(title=_t(u'Destination'), readonly=True,
                                group="Overview")
    nextHop = schema.Entity(title=_t(u"Next Hop"), readonly=True, group="Overview")
    interface = schema.Entity(title=_t(u"Interface"), readonly=True,
                              group="Overview")
    protocol = schema.TextLine(title=_t(u"Protocol"), readonly=True, group="Overview")
    type = schema.TextLine(title=_t(u"Type"), readonly=True, group="Overview")


class ICPUInfo(IComponentInfo):
    """
    Info adapter for CPU components.
    """
    socket = schema.Int(title=_t(u"Socket"), readonly=True)
    clockspeed = schema.Int(title=_t(u"Clock Speed"), readonly=True)
    extspeed = schema.Int(title=_t(u"Ext Speed"), readonly=True)
    voltage = schema.Int(title=_t(u"Voltage"), readonly=True)
    cacheSizeL1 = schema.Int(title=_t(u"L1"), readonly=True)
    cacheSizeL2 = schema.Int(title=_t(u"L2"), readonly=True)
    product = schema.Entity(title=_t(u"Model"), readonly=True)
    manufacturer = schema.Entity(title=_t(u"Manufacturer"), readonly=True)


class IExpansionCardInfo(IComponentInfo):
    """
    Info adapter for ExpansionCard components.
    """
    slot = schema.TextLine(title=_t(u'Slot'), group='Overview', readonly=True)
    serialNumber = schema.TextLine(title=_t(u'Serial Number'), readonly=True)
    product = schema.Entity(title=_t(u'Model'), readonly=True)
    manufacturer = schema.Entity(title=_t(u'Manufacturer'), readonly=True)


class IPowerSupplyInfo(IComponentInfo):
    """
    Info adapter for PowerSupply components.
    """
    watts = schema.Int(title=_t(u'Watts'), group='Overview', readonly=True)
    type = schema.TextLine(title=_t(u'Type'), group='Overview', readonly=True)
    state = schema.TextLine(title=_t(u'State'), group='Overview', readonly=True)
    millivolts = schema.Int(
        title=_t(u'Millivolts'), group='Overview', readonly=True)


class ITemperatureSensorInfo(IComponentInfo):
    """
    Info adapter for TemperatureSensor components.
    """
    state = schema.TextLine(title=_t(u'State'), group='Overview', readonly=True)
    temperature = schema.Int(
        title=_t(u'Temperature (Fahrenheit)'), group='Overview', readonly=True)


class IFanInfo(IComponentInfo):
    """
    Info adapter for Fan components.
    """
    state = schema.TextLine(title=_t(u'State'), group='Overview', readonly=True)
    type = schema.TextLine(title=_t(u'Type'), group='Overview', readonly=True)
    rpm = schema.Int(title=_t(u'RPM'), group='Overview', readonly=True)


class IHardDiskInfo(IComponentInfo):
    """
    Info adapter for HardDisk components.
    """
    description = schema.Text(
        title=_t(u"Description"), group="Overview",
        order=2)

