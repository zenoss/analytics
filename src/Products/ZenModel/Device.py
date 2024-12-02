##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Device

Base device (remote computer) class
"""

import cgi
import itertools
import logging
import socket
import time

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base
from BTrees.OOBTree import OOSet
from DateTime import DateTime
from App.special_dtml import DTMLFile
from ipaddr import IPAddress
from OFS.CopySupport import CopyError
from urllib import quote as urlquote
from zenoss.protocols.protobufs.zep_pb2 import (
    SEVERITY_CRITICAL,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    STATUS_ACKNOWLEDGED,
    STATUS_NEW,
    STATUS_SUPPRESSED,
)
from ZODB.POSException import POSError
from zope.component import subscribers
from zope.event import notify
from zope.interface import implementer

from Products.Jobber.jobs import FacadeMethodJob
from Products.PluginIndexes.FieldIndex.FieldIndex import FieldIndex
from Products.ZenEvents.browser.EventPillsAndSummaries import getEventPillME
from Products.ZenEvents.events2.proxy import EventProxy
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenMessaging.audit import audit
from Products.ZenRelations.RelSchema import ToManyCont, ToMany, ToOne
from Products.ZenUtils import NetworkTree, Time
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.guid.interfaces import (
    IGlobalIdentifier,
    IGloballyIdentifiable,
)
from Products.ZenUtils.IpUtil import (
    checkip,
    getHostByName,
    IpAddressError,
    ipAndMaskFromIpMask,
    ipunwrap,
    maskToBits,
    numbip,
)
from Products.ZenUtils.Search import (
    makeCaseInsensitiveFieldIndex,
    makeCaseInsensitiveKeywordIndex,
    makeMultiPathIndex,
)
from Products.ZenUtils.Utils import (
    edgesToXML,
    getObjectsFromCatalog,
    isXmlRpc,
    unpublished,
    unused,
)
from Products.ZenWidgets import messaging
from Products.ZenWidgets.interfaces import IMessageSender
from Products.Zuul import getFacade
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.indexable import DeviceIndexable
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .AdministrativeRoleable import AdministrativeRoleable
from .Commandable import Commandable
from .DeviceHW import DeviceHW
from .EventView import IEventView
from .Exceptions import DeviceExistsError, NoSnmp
from .interfaces import IExpandedLinkProvider
from .Lockable import Lockable
from .MaintenanceWindowable import MaintenanceWindowable
from .ManagedEntity import ManagedEntity
from .OperatingSystem import OperatingSystem
from .RRDDataSource import isPythonDataSource
from .ZenMenuable import ZenMenuable
from .ZenossSecurity import (
    ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE,
    ZEN_DELETE_DEVICE,
    ZEN_EDIT_LOCAL_TEMPLATES,
    ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS,
    ZEN_MANAGE_DMD,
    ZEN_VIEW,
)
from .ZenStatus import ZenStatus

DEFAULT_PRODSTATE = 1000

_sourcetype_to_collector_map = {
    "Python": "zenpython",
    "SNMP": "zenperfsnmp",
    "COMMAND": "zencommand",
}

log = logging.getLogger("zen.model.device")


def getNetworkRoot(context, performanceMonitor):
    """
    Return the default network root.
    """
    return context.getDmdRoot("Networks")


def manage_createDevice(
    context,
    deviceName,
    devicePath="/Discovered",
    tag="",
    serialNumber="",
    zSnmpCommunity="",
    zSnmpPort=161,
    zSnmpVer="",
    rackSlot="",
    productionState=DEFAULT_PRODSTATE,
    comments="",
    hwManufacturer="",
    hwProductName="",
    osManufacturer="",
    osProductName="",
    locationPath="",
    groupPaths=None,
    systemPaths=None,
    performanceMonitor="localhost",
    discoverProto="snmp",
    priority=3,
    manageIp="",
    zProperties=None,
    title=None,
):
    """
    Device factory creates a device and sets up its relations and collects its
    configuration. SNMP Community discovery also happens here. If an IP is
    passed for deviceName it will be used for collection and the device name
    will be set to the SNMP SysName (or ptr if SNMP Fails and ptr is valid)

    @rtype: Device
    """
    manageIp = manageIp.replace(" ", "")
    deviceName = context.prepId(deviceName)
    deviceClass = context.getDmdRoot("Devices").createOrganizer(devicePath)
    device = deviceClass.createInstance(
        deviceName, performanceMonitor, manageIp
    )
    device.setPerformanceMonitor(performanceMonitor)
    device.setManageIp(manageIp)
    device.manage_editDevice(
        tag,
        serialNumber,
        zSnmpCommunity,
        zSnmpPort,
        zSnmpVer,
        rackSlot,
        productionState,
        comments,
        hwManufacturer,
        hwProductName,
        osManufacturer,
        osProductName,
        locationPath,
        groupPaths if groupPaths else [],
        systemPaths if systemPaths else [],
        performanceMonitor,
        priority,
        zProperties,
        title,
    )
    log.info(
        "created device  name=%s manageIp=%s collector=%s class=%s",
        deviceName,
        manageIp,
        performanceMonitor,
        devicePath,
    )
    return device


def findCommunity(
    context, ip, devicePath, community="", port=None, version=None
):
    """
    Find the SNMP community and version for an IP address using
    zSnmpCommunities.

    @rtype: tuple of (community, port, version, device name)
    """
    from pynetsnmp.SnmpSession import SnmpSession

    devroot = context.getDmdRoot("Devices").createOrganizer(devicePath)
    communities = []
    if community:
        communities.append(community)
    communities.extend(getattr(devroot, "zSnmpCommunities", []))
    if not port:
        port = getattr(devroot, "zSnmpPort", 161)
    versions = ("v2c", "v1")
    if not version:
        version = getattr(devroot, "zSnmpVer", None)
    if version:
        versions = (version,)
    timeout = getattr(devroot, "zSnmpTimeout", 2)
    retries = getattr(devroot, "zSnmpTries", 2)
    session = SnmpSession(ip, timeout=timeout, port=port, retries=retries)
    oid = ".1.3.6.1.2.1.1.5.0"
    goodcommunity = ""
    goodversion = ""
    devname = ""
    for version in versions:
        session.setVersion(version)
        for community in communities:
            session.community = community
            try:
                devname = session.get(oid).values()[0]
                goodcommunity = session.community
                goodversion = version
                break
            except POSError:
                raise
            except Exception:
                pass  # keep trying until we run out
        if goodcommunity:
            break
    else:
        raise NoSnmp("No SNMP found for IP = %s" % ip)
    return (goodcommunity, port, goodversion, devname)


@deprecated  # 1/31/12
def manage_addDevice(context, id, REQUEST=None):
    """
    Creates a device
    """
    serv = Device(id)
    context._setObject(serv.id, serv)
    if REQUEST is not None:
        audit("UI.Device.Add", serv, deviceClass=context)
        REQUEST["RESPONSE"].redirect(
            context.absolute_url_path() + "/manage_main"
        )


addDevice = DTMLFile("dtml/addDevice", globals())


class NoNetMask(Exception):
    pass


@implementer(IEventView, IGloballyIdentifiable)
class Device(
    ManagedEntity,
    Commandable,
    Lockable,
    MaintenanceWindowable,
    AdministrativeRoleable,
    ZenMenuable,
    DeviceIndexable,
):
    """
    Device is a base class that represents the idea of a single computer system
    that is made up of software running on hardware. It currently must be IP
    enabled but maybe this will change.
    """

    event_key = portal_type = meta_type = "Device"

    default_catalog = "deviceSearch"

    relationshipManagerPathRestriction = "/Devices"
    title = ""
    manageIp = ""
    snmpAgent = ""
    snmpDescr = ""
    snmpOid = ""
    snmpContact = ""
    snmpSysName = ""
    snmpLocation = ""
    rackSlot = ""
    comments = ""
    sysedgeLicenseMode = ""
    priority = 3
    macaddresses = None
    renameInProgress = False
    # ZEN-28849: set a default production state for devices
    privateattr_productionState = DEFAULT_PRODSTATE
    _preMWProductionState = DEFAULT_PRODSTATE

    # Flag indicating whether device is in process of creation
    _temp_device = False

    _properties = ManagedEntity._properties + (
        {"id": "title", "type": "string", "mode": "w"},
        {"id": "manageIp", "type": "string", "mode": "w"},
        {"id": "snmpAgent", "type": "string", "mode": "w"},
        {"id": "snmpDescr", "type": "string", "mode": ""},
        {"id": "snmpOid", "type": "string", "mode": ""},
        {"id": "snmpContact", "type": "string", "mode": ""},
        {"id": "snmpSysName", "type": "string", "mode": ""},
        {"id": "snmpLocation", "type": "string", "mode": ""},
        {"id": "snmpLastCollection", "type": "date", "mode": ""},
        {"id": "snmpAgent", "type": "string", "mode": ""},
        {"id": "rackSlot", "type": "string", "mode": "w"},
        {"id": "comments", "type": "text", "mode": "w"},
        {"id": "sysedgeLicenseMode", "type": "string", "mode": ""},
        {"id": "priority", "type": "int", "mode": "w"},
    )

    _relations = ManagedEntity._relations + (
        (
            "deviceClass",
            ToOne(ToManyCont, "Products.ZenModel.DeviceClass", "devices"),
        ),
        (
            "perfServer",
            ToOne(ToMany, "Products.ZenModel.PerformanceConf", "devices"),
        ),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "devices")),
        ("systems", ToMany(ToMany, "Products.ZenModel.System", "devices")),
        ("groups", ToMany(ToMany, "Products.ZenModel.DeviceGroup", "devices")),
        (
            "adminRoles",
            ToManyCont(
                ToOne, "Products.ZenModel.AdministrativeRole", "managedObject"
            ),
        ),
        (
            "userCommands",
            ToManyCont(ToOne, "Products.ZenModel.UserCommand", "commandable"),
        ),
        (
            "ipaddress",
            ToOne(ToOne, "Products.ZenModel.IpAddress", "manageDevice"),
        ),
        # unused:
        (
            "monitors",
            ToMany(ToMany, "Products.ZenModel.StatusMonitorConf", "devices"),
        ),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            "id": "Device",
            "meta_type": "Device",
            "description": """Base class for all devices""",
            "icon": "Device_icon.gif",
            "product": "ZenModel",
            "factory": "manage_addDevice",
            "immediate_view": "devicedetail",
            "actions": (
                {
                    "id": "events",
                    "name": "Events",
                    "action": "viewEvents",
                    "permissions": (ZEN_VIEW,),
                },
                {
                    "id": "perfServer",
                    "name": "Graphs",
                    "action": "viewDevicePerformance",
                    "permissions": (ZEN_VIEW,),
                },
                {
                    "id": "edit",
                    "name": "Edit",
                    "action": "editDevice",
                    "permissions": ("Change Device",),
                },
            ),
        },
    )

    security = ClassSecurityInfo()

    security.declarePrivate("propertyItems")

    def __init__(self, id, buildRelations=True):
        ManagedEntity.__init__(self, id, buildRelations=buildRelations)
        self.resetProductionState()
        osObj = OperatingSystem()
        self._setObject(osObj.id, osObj)
        hw = DeviceHW()
        self._setObject(hw.id, hw)
        # self.commandStatus = "Not Tested"
        self._lastPollSnmpUpTime = ZenStatus(0)
        self._snmpLastCollection = 0
        self._lastChange = 0
        self._create_componentSearch()

    # Resets the production state to the default value
    def resetProductionState(self):
        super(Device, self).resetProductionState()
        self._setProductionState(DEFAULT_PRODSTATE)
        self.setPreMWProductionState(DEFAULT_PRODSTATE)

    def isTempDevice(self):
        flag = getattr(self, "_temp_device", None)
        if flag is None:
            flag = self._temp_device = False
        return flag

    def name(self):
        """
        Return the name of this device.  Default is titleOrId.
        """
        return self.titleOrId()

    security.declareProtected(ZEN_MANAGE_DMD, "changeDeviceClass")

    def changeDeviceClass(self, deviceClassPath, REQUEST=None):
        """
        Wrapper for DeviceClass.moveDevices. The primary reason to use this
        method instead of that one is that this one returns the new path to the
        device.

        @param deviceClassPath: device class in DMD path
        @type deviceClassPath: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        self.deviceClass().moveDevices(deviceClassPath, (self.id,))
        device = self.getDmdRoot("Devices").findDevice(self.id)
        if REQUEST:
            audit(
                "UI.Device.ChangeDeviceClass",
                self,
                deviceClass=deviceClassPath,
            )
        return device.absolute_url_path()

    @deprecated
    def getRRDTemplate(self):
        import warnings

        warnings.warn(
            "Device.getRRDTemplate is deprecated", DeprecationWarning
        )
        return ManagedEntity.getRRDTemplate(self)

    def getRRDTemplates(self):
        """
        Returns all the templates bound to this Device

        @rtype: list
        """
        if not hasattr(self, "zDeviceTemplates"):
            return ManagedEntity.getRRDTemplates(self)
        templates = []
        for templateName in self.zDeviceTemplates:
            if templateName.endswith("-replacement") or templateName.endswith(
                "-addition"
            ):
                continue

            template = self.getRRDTemplateByName(templateName)
            if not template:
                continue
            replacement = self.getRRDTemplateByName(
                "{}-replacement".format(templateName)
            )

            if replacement and replacement not in templates:
                templates.append(replacement)
            else:
                templates.append(template)

            addition = self.getRRDTemplateByName(
                "{}-addition".format(templateName)
            )

            if addition and addition not in templates:
                templates.append(addition)

        return templates

    def getDataSourceOptions(self):
        """
        Returns the available DataSource options. DataSource options
        are used to populate the dropdown when adding a new DataSource
        and is a string.  See L{RRDTemplate.RRDTemplate.getDataSourceOptions}
        for more information.

        @rtype: list
        @return: [(displayName, dsOption),]
        """
        # This is an unfortunate hack.  Called from the device templates
        # page where we show multiple templates now.  This only really
        # works because getDataSourceOptions() returns the same values
        # for every template.  Ideally we would be able to pass some sort
        # of context to the Add DataSource dialog that calls this method.
        templates = self.getRRDTemplates()
        if templates:
            return templates[0].getDataSourceOptions()
        return []

    def sysUpTime(self):
        """
        Returns the cached sysUpTime for this device

        @rtype: int
        """
        try:
            return self.cacheRRDValue("sysUpTime", -1)
        except Exception:
            log.exception("failed getting sysUpTime")
            return -1

    def availability(self, *args, **kw):
        """
        Returns the uptime of this device

        @rtype: string
        @todo: Performance enhancement: Should move import outside of method
        """
        from Products.ZenEvents import Availability

        results = Availability.query(self.dmd, device=self.id, *args, **kw)
        if results:
            return results[0]
        else:
            return None

    # FIXME: cleanup --force option #2660
    def __getattr__(self, name):
        """
        Override from object to handle lastPollSnmpUpTime and
        snmpLastCollection

        @todo: Not sure this is needed, see getLastPollSnmpUpTime and
        getSnmpLastCollection
        """
        if name == "lastPollSnmpUpTime":
            return self._lastPollSnmpUpTime.getStatus()
        elif name == "snmpLastCollection":
            return DateTime(self._snmpLastCollection)
        else:
            raise AttributeError(name)

    def _setPropValue(self, id, value):
        """
        Override from PropertyManager to handle checks and ip creation

        @todo: Not sure this is needed, see setSnmpLastCollection
        """
        self._wrapperCheck(value)
        if id == "snmpLastCollection":
            self._snmpLastCollection = float(value)
        else:
            ManagedEntity._setPropValue(self, id, value)

    security.declareProtected(ZEN_MANAGE_DEVICE, "applyDataMap")

    def applyDataMap(
        self, datamap, relname="", compname="", modname="", parentId=""
    ):
        """
        Apply a datamap passed as a list of dicts through XML-RPC.
        """
        from Products.DataCollector.ApplyDataMap import ApplyDataMap

        adm = ApplyDataMap()
        return adm.applyDataMap(
            self,
            datamap,
            relname=relname,
            compname=compname,
            modname=modname,
            parentId="",
        )

    def path(self):
        """
        Return a sequence of path tuples suitable for indexing by
        a MultiPathIndex.
        """
        orgs = (
            self.systems()
            + self.groups()
            + [self.location()]
            + [self.deviceClass()]
        )
        return [
            aq_base(self).__of__(o.primaryAq()).getPhysicalPath()
            for o in orgs
            if o is not None
        ]

    def traceRoute(self, target, ippath=None):
        """
        Trace the route to target using our routing table.
        Wrapper method of OperatingSystem.traceRoute

        @param target: Device name
        @type target: string
        @param ippath: IP addesses
        @type ippath: list
        @return: IP Addresses
        @rtype: list
        """
        if ippath is None:
            ippath = []
        if isinstance(target, basestring):
            target = self.findDevice(target)
            if not target:
                raise ValueError("Target %s not found in DMD" % target)
        return self.os.traceRoute(target, ippath)

    def getMonitoredComponents(self, collector=None, type=None):
        """
        Return list of monitored DeviceComponents on this device.
        Wrapper method for getDeviceComponents
        """
        components = self.getDeviceComponents(
            monitored=True, collector=collector, type=type
        )
        return filter(
            lambda x: x.getProductionState() >= x.zProdStateThreshold,
            components,
        )

    security.declareProtected(ZEN_VIEW, "getReportableComponents")

    def getReportableComponents(self, collector=None, type=None):
        """
        Return a list of DeviceComponents on this device that should be
        considered for reporting.

        @type collector: string
        @type type: string
        @permission: ZEN_VIEW
        @rtype: list
        """
        return self.getMonitoredComponents(collector=collector, type=type)

    def _createComponentSearchPathIndex(self):
        indexName = "getAllPaths"
        if indexName not in self.componentSearch.indexes():
            zcat = self._getOb("componentSearch")
            cat = zcat._catalog
            cat.addIndex(indexName, makeMultiPathIndex(indexName))
            for c in self.getDeviceComponentsNoIndexGen():
                c.index_object(idxs=[indexName])

    def _create_componentSearch(self):
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        manage_addZCatalog(self, "componentSearch", "componentSearch")
        zcat = self._getOb("componentSearch")

        cat = zcat._catalog
        cat.addIndex("meta_type", makeCaseInsensitiveFieldIndex("meta_type"))
        cat.addIndex(
            "getCollectors", makeCaseInsensitiveKeywordIndex("getCollectors")
        )
        cat.addIndex("id", makeCaseInsensitiveFieldIndex("id"))
        cat.addIndex("titleOrId", makeCaseInsensitiveFieldIndex("titleOrId"))

        zcat.addIndex("monitored", FieldIndex("monitored"))
        zcat.addColumn("meta_type")
        zcat.addColumn("getUUID")
        zcat.addColumn("id")
        zcat.addColumn("titleOrId")
        zcat.addColumn("description")

        for c in self.getDeviceComponentsNoIndexGen():
            c.index_object()
        # See ZEN-4087 double index the first component when creating this
        # catalog, otherwise it will not appear in the list of components.
        if len(self.componentSearch):
            self.componentSearch()[0].getObject().index_object()

    def getDeviceComponents_from_model_catalog(
        self, monitored=None, collector=None, type=None
    ):
        """
        Return list of all DeviceComponents on this device extracted from
        model catalog. not used for now.

        @type monitored: boolean
        @type collector: string
        @type type: string
        @permission: ZEN_VIEW
        @rtype: list
        """
        query = {
            "objectImplements": (
                "Products.ZenModel.DeviceComponent.DeviceComponent"
            )
        }
        if collector is not None:
            query["collectors"] = collector
        if monitored is not None:
            query["monitored"] = monitored
        if type is not None:
            query["meta_type"] = type

        cat = IModelCatalogTool(self)
        search_results = cat.search(query=query)
        results = []
        if search_results.total > 0:
            results = [brain.getObject() for brain in search_results.results]
        return results

    security.declareProtected(ZEN_VIEW, "getDeviceComponents")

    def getDeviceComponents(self, monitored=None, collector=None, type=None):
        """
        Return list of all DeviceComponents on this device.

        @type monitored: boolean
        @type collector: string
        @type type: string
        @permission: ZEN_VIEW
        @rtype: list
        """
        # Auto-migrate component catalog for this device
        # See ZEN-2537 for reason for this change
        if getattr(aq_base(self), "componentSearch", None) is None:
            self._create_componentSearch()

        query = {}
        if collector is not None:
            query["getCollectors"] = collector
        if monitored is not None:
            query["monitored"] = monitored
        if type is not None:
            query["meta_type"] = type

        return list(getObjectsFromCatalog(self.componentSearch, query, log))

    def getDeviceComponentsNoIndexGen(self):
        """
        Return a list of all device components by walking relations.  This is
        much slower then the normal getDeviceComponents method which uses the
        component index.  It is used when rebuilding the device indexes.
        """
        from DeviceComponent import DeviceComponent

        for baseObject in (self, self.os, self.hw):
            for rel in baseObject.getRelationships():
                if rel.meta_type != "ToManyContRelationship":
                    continue
                for obj in rel():
                    if not isinstance(obj, DeviceComponent):
                        break
                    for subComp in obj.getSubComponentsNoIndexGen():
                        yield subComp
                    yield obj

    def getSnmpConnInfo(self):
        """
        Returns an object containing SNMP Connection Info

        @rtype: SnmpConnInfo object
        """
        from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo

        return SnmpConnInfo(self)

    def getHWManufacturerName(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.getManufacturerName()

    def getHWProductName(self):
        """
        Return the hardware product name of this device.

        @rtype: string
        """
        return self.hw.getProductName()

    def getHWProductClass(self):
        """
        Return the hardware product class of this device.

        @rtype: string
        """
        cls = self.hw.productClass()
        if cls:
            return cls.titleOrId()

    def getHWProductKey(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.getProductKey()

    def getOSManufacturerName(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getManufacturerName()

    def getOSProductName(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getProductName()

    def getOSProductKey(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getProductKey()

    security.declareProtected(ZEN_CHANGE_DEVICE, "setOSProductKey")

    def setOSProductKey(self, prodKey, manufacturer=None):
        """
        Set the productKey of the device OS.
        """
        self.os.setProductKey(prodKey, manufacturer)

    def getHWTag(self):
        """
        @rtype: string
        @todo: remove this method and remove the call from testDevice.py
        """
        return self.hw.tag

    security.declareProtected(ZEN_CHANGE_DEVICE, "setHWTag")

    def setHWTag(self, assettag):
        """
        Set the asset tag of the device hardware.
        """
        self.hw.tag = assettag

    security.declareProtected(ZEN_CHANGE_DEVICE, "setHWProductKey")

    def setHWProductKey(self, prodKey, manufacturer=None):
        """
        Set the productKey of the device hardware.
        """
        self.hw.setProductKey(prodKey, manufacturer)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setHWSerialNumber")

    def setHWSerialNumber(self, number):
        """
        Set the hardware serial number.
        """
        self.hw.serialNumber = number

    def getHWSerialNumber(self):
        """
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.serialNumber

    def followNextHopIps(self):
        """
        Return the ips that our indirect routs point to which aren't currently
        connected to devices.

        @todo: Can be moved to zendisc.py
        """
        ips = []
        for r in self.os.routes():
            ipobj = r.nexthop()
            # if ipobj and not ipobj.device():
            if ipobj:
                ips.append(ipobj.id)
        return ips

    security.declareProtected(ZEN_VIEW, "getLocationName")

    def getLocationName(self):
        """
        Return the location name. i.e. "Rack" from /Locations/Loc/SubLoc/Rack

        @rtype: string
        @permission: ZEN_VIEW
        """
        loc = self.location()
        if loc:
            return loc.getOrganizerName()
        return ""

    security.declareProtected(ZEN_VIEW, "getLocationLink")

    def getLocationLink(self):
        """
        Return a link to the device's location.

        @rtype: string
        @permission: ZEN_VIEW
        """
        loc = self.location()
        if loc:
            if self.checkRemotePerm(ZEN_VIEW, loc):
                return "<a href='%s'>%s</a>" % (
                    loc.getPrimaryUrlPath(),
                    loc.getOrganizerName(),
                )
            else:
                return loc.getOrganizerName()
        return "None"

    security.declareProtected(ZEN_VIEW, "getSystemNames")

    def getSystemNames(self):
        """
        Return the system names for this device

        @rtype: list
        @permission: ZEN_VIEW
        """
        return map(lambda x: x.getOrganizerName(), self.systems())

    security.declareProtected(ZEN_VIEW, "getSystemNamesString")

    def getSystemNamesString(self, sep=", "):
        """
        Return the system names for this device as a string

        @rtype: string
        @permission: ZEN_VIEW
        """
        return sep.join(self.getSystemNames())

    security.declareProtected(ZEN_VIEW, "getDeviceGroupNames")

    def getDeviceGroupNames(self):
        """
        Return the device group names for this device

        @rtype: list
        @permission: ZEN_VIEW
        """
        return map(lambda x: x.getOrganizerName(), self.groups())

    security.declareProtected(ZEN_VIEW, "getPerformanceServer")

    def getPerformanceServer(self):
        """
        Return the device performance server

        @rtype: PerformanceMonitor
        @permission: ZEN_VIEW
        """
        return self.perfServer()

    security.declareProtected(ZEN_VIEW, "getPerformanceServerName")

    def getPerformanceServerName(self):
        """
        Return the device performance server name

        @rtype: string
        @permission: ZEN_VIEW
        """
        cr = self.perfServer()
        if cr:
            return cr.getId()
        return ""

    def getNetworkRoot(self, version=None):
        """Return the network root object"""
        return self.getDmdRoot("Networks").getNetworkRoot(version)

    security.declareProtected(ZEN_VIEW, "getLastChange")

    def getLastChange(self):
        """
        Return DateTime of last change detected on this device.

        @rtype: DateTime
        @permission: ZEN_VIEW
        """
        return DateTime(float(self._lastChange))

    security.declareProtected(ZEN_VIEW, "getLastChangeString")

    def getLastChangeString(self):
        """
        Return date string of last change detected on this device.

        @rtype: string
        @permission: ZEN_VIEW
        """
        return Time.LocalDateTimeSecsResolution(float(self._lastChange))

    security.declareProtected(ZEN_VIEW, "getSnmpLastCollection")

    def getSnmpLastCollection(self):
        """
        Return DateTime of last SNMP collection on this device.

        @rtype: DateTime
        @permission: ZEN_VIEW
        """
        return DateTime(float(self._snmpLastCollection))

    security.declareProtected(ZEN_VIEW, "getSnmpLastCollectionString")

    def getSnmpLastCollectionString(self):
        """
        Return date string of last SNMP collection on this device.

        @rtype: string
        @permission: ZEN_VIEW
        """
        if self._snmpLastCollection:
            return Time.LocalDateTimeSecsResolution(
                float(self._snmpLastCollection)
            )
        return "Not Modeled"

    def _sanitizeIPaddress(self, ip):
        try:
            if not ip:
                pass  # Forcing a reset with a blank IP
            elif ip.find("/") > -1:
                ipWithoutNetmask, netmask = ip.split("/", 1)
                checkip(ipWithoutNetmask)
                # Also check for valid netmask if they give us one
                if maskToBits(netmask) is None:
                    raise NoNetMask()
            else:
                checkip(ip)
            if ip:
                # Strip out subnet mask before checking if it's a good IP
                netmask = ""
                if "/" in ip:
                    netmask = ip.split("/")[1]
                ip = str(IPAddress(ipunwrap(ip.split("/")[0])))
                if netmask:
                    ip = "/".join([ip, netmask])
        except (IpAddressError, ValueError, NoNetMask):
            log.warn("%s is an invalid IP address", ip)
            ip = ""
        return ip

    def _isDuplicateIp(self, ip):
        ipMatch = self.getNetworkRoot().findIp(ip)
        if ipMatch:
            dev = ipMatch.manageDevice()
            if dev and self.id != dev.id:
                return True
        return False

    security.declareProtected(ZEN_ADMIN_DEVICE, "setManageIp")

    def setManageIp(self, ip="", REQUEST=None):
        """
        Set the manage IP, if IP is not passed perform DNS lookup.
        If there is an error with the IP address format, the IP address
        will be reset to the result of a DNS lookup.

        @rtype: string
        @permission: ZEN_ADMIN_DEVICE
        """
        message = ""
        ip = ip.replace(" ", "")
        origip = ip
        ip = self._sanitizeIPaddress(ip)

        if not ip:  # What if they put in a DNS name?
            try:
                ip = getHostByName(origip)
                if ip == "0.0.0.0":
                    # Host resolution failed
                    ip = ""
            except socket.error:
                ip = ""

        if not ip:
            try:
                ip = getHostByName(ipunwrap(self.id))
            except socket.error:
                ip = ""
                if origip:
                    message = (
                        "%s is an invalid IP address, "
                        "and no appropriate IP could"
                        " be found via DNS for %s"
                    ) % (origip, self.id)
                    log.warn(message)
                else:
                    message = (
                        "DNS lookup of '%s' failed to return an IP" % self.id
                    )

        if ip:
            if self._isDuplicateIp(ip):
                message = "The IP address %s is already assigned" % ip
                log.warn(message)

            else:
                self.manageIp = ip
                notify(
                    IndexingEvent(
                        self, ("decimal_ipAddress", "text_ipAddress"), True
                    )
                )
                log.info("%s's IP address has been set to %s.", self.id, ip)
                # Create a new IpAddress object from manageIp under the Network
                ipWithoutNetmask, netmask = ipAndMaskFromIpMask(ip)
                ipobj = self.getNetworkRoot().createIp(
                    ipWithoutNetmask, netmask
                )
                self.ipaddress.addRelation(ipobj)
                notify(IndexingEvent(ipobj))
                if REQUEST:
                    audit("UI.Device.ResetIP", self, ip=ip)

        return message

    security.declareProtected(ZEN_VIEW, "getManageIp")

    def getManageIp(self):
        """
        Return the management ip for this device.

        @rtype: string
        @permission: ZEN_VIEW
        """
        return self.manageIp

    @deprecated
    def getManageIpObj(self):
        """
        DEPRECATED - Return the management ipobject for this device.

        @rtype: IpAddress
        @todo: This method may not be called anywhere, remove it.
        """
        if self.manageIp:
            return self.Networks.findIp(self.manageIp)

    security.declareProtected(ZEN_VIEW, "getManageInterface")

    def getManageInterface(self):
        """
        Return the management interface of a device based on its manageIp.

        @rtype: IpInterface
        @permission: ZEN_VIEW
        """
        ipobj = self.Networks.findIp(self.manageIp)
        if ipobj:
            return ipobj.interface()

    security.declareProtected(ZEN_VIEW, "uptimeStr")

    def uptimeStr(self):
        """
        Return the SNMP uptime

        @rtype: string
        @permission: ZEN_VIEW
        """
        ut = self.sysUpTime()
        # test if less than 0 or NaN
        if ut < 0 or ut != ut:
            return "Unknown"
        elif ut == 0:
            return "0d:0h:0m:0s"
        ut = float(ut) / 100.0
        days = int(ut / 86400)
        hour = int((ut % 86400) / 3600)
        mins = int((ut % 3600) / 60)
        secs = int(ut % 60)
        return "%02dd:%02dh:%02dm:%02ds" % (days, hour, mins, secs)

    def getPeerDeviceClassNames(self):
        """
        Build a list of all device paths that have the python class pyclass

        @rtype: list
        """
        dclass = self.getDmdRoot("Devices")
        return dclass.getPeerDeviceClassNames(self.__class__)

    ####################################################################
    # Edit functions used to manage device relations and other attributes
    ####################################################################

    security.declareProtected(ZEN_CHANGE_DEVICE, "manage_snmpCommunity")

    def manage_snmpCommunity(self):
        """
        Reset the snmp community using the zSnmpCommunities variable.

        @permission: ZEN_CHANGE_DEVICE
        """
        try:
            zSnmpCommunity, zSnmpPort, zSnmpVer, snmpname = findCommunity(
                self,
                self.manageIp,
                self.getDeviceClassPath(),
                port=self.zSnmpPort,
                version=self.zSnmpVer,
            )
        except NoSnmp:
            pass
        else:
            if self.zSnmpCommunity != zSnmpCommunity:
                self.setZenProperty("zSnmpCommunity", zSnmpCommunity)
            if self.zSnmpPort != zSnmpPort:
                self.setZenProperty("zSnmpPort", zSnmpPort)
            if self.zSnmpVer != zSnmpVer:
                self.setZenProperty("zSnmpVer", zSnmpVer)

    def setProductInfo(
        self,
        hwManufacturer="",
        hwProductName="",
        osManufacturer="",
        osProductName="",
    ):
        if hwManufacturer and hwProductName:
            # updateDevice uses the sentinel value "_no_change" to indicate
            # that we really don't want change this value
            if (
                hwManufacturer != "_no_change"
                and hwProductName != "_no_change"
            ):
                log.info(
                    "setting hardware manufacturer to %r productName to %r",
                    hwManufacturer,
                    hwProductName,
                )
                self.hw.setProduct(hwProductName, hwManufacturer)
        else:
            self.hw.removeProductClass()

        if osManufacturer and osProductName:
            # updateDevice uses the sentinel value "_no_change" to indicate
            # that we really don't want change this value
            if (
                osManufacturer != "_no_change"
                and osProductName != "_no_change"
            ):
                log.info(
                    "setting os manufacturer to %r productName to %r",
                    osManufacturer,
                    osProductName,
                )
                self.os.setProduct(osProductName, osManufacturer, isOS=True)
        else:
            self.os.removeProductClass()

    security.declareProtected(ZEN_CHANGE_DEVICE, "updateDevice")

    def updateDevice(self, **kwargs):
        """
        Update the device relation and attributes, if passed. If any parameter
        is not passed it will not be updated; the value of any unpassed device
        propeties will remain the same.

        @permission: ZEN_CHANGE_DEVICE
        Keyword arguments:
          title              -- device title [string]
          tag                -- tag number [string]
          serialNumber       -- serial number [string]
          zProperties        -- dict of zProperties [dict]
          zSnmpCommunity     -- snmp community (overrides corresponding
                                value is zProperties) [string]
          zSnmpPort          -- snmp port (overrides corresponding value
                                in zProperties) [string]
          zSnmpVer           -- snmp version (overrides corresponding value
                                in zProperties) [string]
          rackSlot           -- rack slot number [integer]
          productionState    -- production state of device [integer]
          priority           -- device priority [integer]
          comment            -- device comment [string]
          hwManufacturer     -- hardware manufacturer [string]
          hwProductName      -- hardware product name [string]
          osManufacturer     -- operating system manufacturer [string]
          osProductName      -- operating system name [string]
          locationPath       -- location [string]
          groupPaths         -- group paths [list]
          systemPaths        -- systen paths [list]
          performanceMonitor -- collector name [string]

        """
        if "title" in kwargs and kwargs["title"] is not None:
            newTitle = str(kwargs["title"]).strip()
            if newTitle and newTitle != self.title:
                log.info("setting title to %r", newTitle)
                self.title = newTitle
        if (
            "tag" in kwargs
            and kwargs["tag"] is not None
            and kwargs["tag"] != self.hw.tag
        ):
            log.info("setting tag to %r", kwargs["tag"])
            self.hw.tag = kwargs["tag"]
        if (
            "serialNumber" in kwargs
            and kwargs["serialNumber"] is not None
            and kwargs["serialNumber"] != self.hw.serialNumber
        ):
            log.info("setting serialNumber to %r", kwargs["serialNumber"])
            self.hw.serialNumber = kwargs["serialNumber"]

        # Set zProperties passed in intelligently
        if "zProperties" in kwargs and kwargs["zProperties"] is not None:
            zProperties = kwargs["zProperties"]
        else:
            zProperties = {}

        # override any snmp properties that may be in zProperties
        zpropUpdate = dict(
            (name, kwargs[name])
            for name in ("zSnmpCommunity", "zSnmpPort", "zSnmpVer")
            if name in kwargs
        )
        zProperties.update(zpropUpdate)

        # apply any zProperties to self
        for prop, value in zProperties.items():
            if value is not None and value != "":
                # setZenProperty doesn't set it if it's the same value, so no
                # need to check here
                self.setZenProperty(prop, value)

        if "rackSlot" in kwargs and kwargs["rackSlot"] != self.rackSlot:
            # rackSlot may be a string or integer
            log.info("setting rackSlot to %r", kwargs["rackSlot"])
            self.rackSlot = kwargs["rackSlot"]

        if "productionState" in kwargs:
            # Always set production state,
            # but don't log it if it didn't change.
            if kwargs["productionState"] != self.getProductionState():
                prodStateName = self.dmd.convertProdState(
                    int(kwargs["productionState"])
                )
                log.info("setting productionState to %s", prodStateName)
            self.setProdState(kwargs["productionState"])

        if "priority" in kwargs and int(kwargs["priority"]) != self.priority:
            priorityName = self.dmd.convertPriority(kwargs["priority"])
            log.info("setting priority to %s", priorityName)
            self.setPriority(kwargs["priority"])

        if "comments" in kwargs and kwargs["comments"] != self.comments:
            log.info("setting comments to %r", kwargs["comments"])
            self.comments = kwargs["comments"]

        self.setProductInfo(
            hwManufacturer=kwargs.get("hwManufacturer", "_no_change"),
            hwProductName=kwargs.get("hwProductName", "_no_change"),
            osManufacturer=kwargs.get("osManufacturer", "_no_change"),
            osProductName=kwargs.get("osProductName", "_no_change"),
        )

        if kwargs.get("locationPath", False):
            log.info("setting location to %r", kwargs["locationPath"])
            self.setLocation(kwargs["locationPath"])

        if kwargs.get("groupPaths", False):
            log.info("setting group %r", kwargs["groupPaths"])
            self.setGroups(kwargs["groupPaths"])

        if kwargs.get("systemPaths", False):
            log.info("setting system %r", kwargs["systemPaths"])
            self.setSystems(kwargs["systemPaths"])

        if (
            "performanceMonitor" in kwargs
            and kwargs["performanceMonitor"] != self.getPerformanceServerName()
        ):
            log.info(
                "setting performance monitor to %r",
                kwargs["performanceMonitor"],
            )
            self.setPerformanceMonitor(kwargs["performanceMonitor"])

        self.setLastChange()
        notify(IndexingEvent(self))

    security.declareProtected(ZEN_CHANGE_DEVICE, "manage_editDevice")

    def manage_editDevice(
        self,
        tag="",
        serialNumber="",
        zSnmpCommunity=None,
        zSnmpPort=161,
        zSnmpVer=None,
        rackSlot="",
        productionState=DEFAULT_PRODSTATE,
        comments="",
        hwManufacturer="",
        hwProductName="",
        osManufacturer="",
        osProductName="",
        locationPath="",
        groupPaths=[],
        systemPaths=[],
        performanceMonitor="localhost",
        priority=3,
        zProperties=None,
        title=None,
        REQUEST=None,
    ):
        """
        Edit the device relation and attributes.
        This method will update device properties because of the default
        values that are passed. Calling this method using a **kwargs dict will
        result in default values being set for many device properties.  To
        update only a subset of these properties use updateDevice(**kwargs).

        @param locationPath: path to a Location
        @type locationPath: string
        @param groupPaths: paths to DeviceGroups
        @type groupPaths: list
        @param systemPaths: paths to Systems
        @type systemPaths: list
        @param performanceMonitor: name of PerformanceMonitor
        @type performanceMonitor: string
        @permission: ZEN_CHANGE_DEVICE
        """
        self.updateDevice(
            tag=tag,
            serialNumber=serialNumber,
            zSnmpCommunity=zSnmpCommunity,
            zSnmpPort=zSnmpPort,
            zSnmpVer=zSnmpVer,
            rackSlot=rackSlot,
            productionState=productionState,
            comments=comments,
            hwManufacturer=hwManufacturer,
            hwProductName=hwProductName,
            osManufacturer=osManufacturer,
            osProductName=osProductName,
            locationPath=locationPath,
            groupPaths=groupPaths,
            systemPaths=systemPaths,
            performanceMonitor=performanceMonitor,
            priority=priority,
            zProperties=zProperties,
            title=title,
            REQUEST=REQUEST,
        )
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage

            IMessageSender(self).sendToBrowser("Saved", SaveMessage())
            # TODO: Audit all of the changed values.
            #       How is this method called to test the output?
            #       Will the [zProperties] field show password values?
            audit("UI.Device.Edit", self)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setTitle")

    def setTitle(self, newTitle):
        """
        Changes the title to newTitle and reindexes the object
        """
        super(Device, self).setTitle(newTitle)
        notify(IndexingEvent(self, ("name",), True))

    def monitorDevice(self):
        """
        Returns true if the device production state >= zProdStateThreshold.

        @rtype: boolean
        """
        return (
            self.getProductionState() >= self.zProdStateThreshold
            and not self.renameInProgress
        )

    def snmpMonitorDevice(self):
        """
        Returns true if the device is subject to SNMP monitoring

        @rtype: boolean
        """
        return (
            self.monitorDevice()
            and self.getManageIp()
            and not self.zSnmpMonitorIgnore
        )

    def getPriority(self):
        """
        Return the numeric device priority.

        @rtype: int
        """
        return self.priority

    def getPriorityString(self):
        """
        Return the device priority as a string.

        @rtype: string
        """
        return str(self.convertPriority(self.priority))

    def getPingStatusString(self):
        """
        Return the pingStatus as a string

        @rtype: string
        """
        result = self.getPingStatus()
        if result <= 0:
            return str(self.convertStatus(result))
        return "Down"

    def getSnmpStatusString(self):
        """
        Return the snmpStatus as a string

        @rtype: string
        """
        result = self.getSnmpStatus()
        if result <= 0:
            return str(self.convertStatus(result))
        return "Down"

    security.declareProtected(ZEN_CHANGE_DEVICE_PRODSTATE, "setProdState")

    def setProdState(self, state, maintWindowChange=False, REQUEST=None):
        """
        Set the device's production state.

        @parameter state: new production state
        @type state: int
        @parameter maintWindowChange: are we resetting state from inside a MW?
        @type maintWindowChange: boolean
        @permission: ZEN_CHANGE_DEVICE
        """
        # Set production state on all components that inherit from this device
        ret = super(Device, self).setProdState(
            state, maintWindowChange, REQUEST
        )
        self._p_changed = True
        if REQUEST:
            audit(
                "UI.Device.Edit",
                self,
                productionState=state,
                maintenanceWindowChange=maintWindowChange,
            )
        return ret

    security.declareProtected(ZEN_CHANGE_DEVICE, "setPriority")

    def setPriority(self, priority, REQUEST=None):
        """
        Set the device's priority

        @type priority: int
        @permission: ZEN_CHANGE_DEVICE
        """
        self.priority = int(priority)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Priority Updated",
                "Device priority has been set to %s."
                % (self.getPriorityString()),
            )
            audit("UI.Device.Edit", self, priority=priority)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setLastChange")

    def setLastChange(self, value=None):
        """
        Set the changed datetime for this device.

        @param value: secs since the epoch, default is now
        @type value: float
        @permission: ZEN_CHANGE_DEVICE
        """
        if value is None:
            value = time.time()
        self._lastChange = float(value)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setSnmpLastCollection")

    def setSnmpLastCollection(self, value=None):
        """
        Set the last time snmp collection occurred.

        @param value: secs since the epoch, default is now
        @type value: float
        @permission: ZEN_CHANGE_DEVICE
        """
        if value is None:
            value = time.time()
        self._snmpLastCollection = float(value)

    security.declareProtected(ZEN_CHANGE_DEVICE, "addManufacturer")

    def addManufacturer(
        self,
        newHWManufacturerName=None,
        newSWManufacturerName=None,
        REQUEST=None,
    ):
        """
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        mname = newHWManufacturerName
        field = "hwManufacturer"
        if not mname:
            mname = newSWManufacturerName
            field = "osManufacturer"
        self.getDmdRoot("Manufacturers").createManufacturer(mname)
        if REQUEST:
            REQUEST[field] = mname
            messaging.IMessageSender(self).sendToBrowser(
                "Manufacturer Added",
                "The %s manufacturer has been created." % mname,
            )
            audit("UI.Device.AddManufacturer", self, manufacturer=mname)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setHWProduct")

    def setHWProduct(
        self, newHWProductName=None, hwManufacturer=None, REQUEST=None
    ):
        """
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        added = False
        if newHWProductName and hwManufacturer:
            self.getDmdRoot("Manufacturers").createHardwareProduct(
                newHWProductName, hwManufacturer
            )
            added = True
        if REQUEST:
            if added:
                messaging.IMessageSender(self).sendToBrowser(
                    "Product Set",
                    "Hardware product has been set to %s." % newHWProductName,
                )
                REQUEST["hwProductName"] = newHWProductName
                audit(
                    "UI.Device.SetHWProduct",
                    self,
                    manufacturer=hwManufacturer,
                    product=newHWProductName,
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    "Set Product Failed",
                    "Hardware product could not be set to %s."
                    % newHWProductName,
                    priority=messaging.WARNING,
                )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setOSProduct")

    def setOSProduct(
        self, newOSProductName=None, osManufacturer=None, REQUEST=None
    ):
        """
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        if newOSProductName:
            self.getDmdRoot("Manufacturers").createSoftwareProduct(
                newOSProductName, osManufacturer, isOS=True
            )
        if REQUEST:
            if newOSProductName:
                messaging.IMessageSender(self).sendToBrowser(
                    "Product Set",
                    "OS product has been set to %s." % newOSProductName,
                )
                REQUEST["osProductName"] = newOSProductName
                audit(
                    "UI.Device.SetOSProduct",
                    self,
                    manufacturer=osManufacturer,
                    product=newOSProductName,
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    "Set Product Failed",
                    "OS product could not be set to %s." % newOSProductName,
                    priority=messaging.WARNING,
                )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setLocation")

    def setLocation(self, locationPath, REQUEST=None):
        """
        Set the location of a device.
        If the location is new it will be created.

        @permission: ZEN_CHANGE_DEVICE
        """
        if not locationPath:
            self.location.removeRelation()
        else:
            locobj = self.getDmdRoot("Locations").createOrganizer(locationPath)
            self.addRelation("location", locobj)
        self.setAdminLocalRoles()
        notify(IndexingEvent(self, "path", False))
        if REQUEST:
            action = "SetLocation" if locationPath else "RemoveFromLocation"
            audit(["UI.Device", action], self, location=locationPath)

    security.declareProtected(ZEN_CHANGE_DEVICE, "addLocation")

    def addLocation(self, newLocationPath, REQUEST=None):
        """
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        if REQUEST:
            REQUEST["locationPath"] = newLocationPath
            messaging.IMessageSender(self).sendToBrowser(
                "Location Added",
                "Location %s has been created." % newLocationPath,
            )
            audit("UI.Device.SetLocation", self, location=newLocationPath)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setPerformanceMonitor")

    def setPerformanceMonitor(
        self, performanceMonitor, newPerformanceMonitor=None, REQUEST=None
    ):
        """
        Set the performance monitor for this device.
        If newPerformanceMonitor is passed in create it

        @permission: ZEN_CHANGE_DEVICE
        """
        if newPerformanceMonitor:
            performanceMonitor = newPerformanceMonitor

        if self.getPerformanceServer() is not None:
            oldPerformanceMonitor = self.getPerformanceServer().getId()
            self.getDmdRoot("Monitors").setPreviousCollectorForDevice(
                self.getId(), oldPerformanceMonitor
            )

        collectorNotFound = False
        warning = None
        obj = self.getDmdRoot("Monitors").getPerformanceMonitor(
            performanceMonitor
        )
        if obj.viewName() != performanceMonitor:
            collectorNotFound = True
            warning = (
                "Collector {} is not found. "
                "Performance monitor has been set to {}.".format(
                    performanceMonitor, obj.viewName()
                )
            )
            log.warn(warning)
        self.addRelation("perfServer", obj)
        self.setLastChange()
        notify(IndexingEvent(self))

        if REQUEST:
            message = "Performance monitor has been set to {}.".format(
                performanceMonitor
            )
            if collectorNotFound:
                message = warning
            messaging.IMessageSender(self).sendToBrowser(
                "Monitor Changed", message
            )
            audit(
                "UI.Device.SetPerformanceMonitor",
                self,
                performancemonitor=performanceMonitor,
            )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setGroups")

    def setGroups(self, groupPaths):
        """
        Set the list of groups for this device based on a list of paths

        @permission: ZEN_CHANGE_DEVICE
        """
        objGetter = self.getDmdRoot("Groups").createOrganizer
        self._setRelations("groups", objGetter, groupPaths)
        notify(IndexingEvent(self, "path", False))

    security.declareProtected(ZEN_CHANGE_DEVICE, "addDeviceGroup")

    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """
        DEPRECATED?
        Add a device group to the database and this device

        @permission: ZEN_CHANGE_DEVICE
        @todo: Already exists on ZDeviceLoader
        """
        group = self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        self.addRelation("groups", group)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Group Added",
                "Group %s has been created." % newDeviceGroupPath,
            )
            audit("UI.Device.AddToGroup", self, group=newDeviceGroupPath)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setSystems")

    def setSystems(self, systemPaths):
        """
        Set a list of systems to this device using their system paths

        @permission: ZEN_CHANGE_DEVICE
        """
        objGetter = self.getDmdRoot("Systems").createOrganizer
        self._setRelations("systems", objGetter, systemPaths)
        notify(IndexingEvent(self, "path", False))

    security.declareProtected(ZEN_CHANGE_DEVICE, "addSystem")

    def addSystem(self, newSystemPath, REQUEST=None):
        """
        DEPRECATED?
        Add a systems to this device using its system path

        @permission: ZEN_CHANGE_DEVICE
        @todo: Already exists on ZDeviceLoader
        """
        sys = self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        self.addRelation("systems", sys)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "System Added", "System %s has been created." % newSystemPath
            )
            audit("UI.Device.AddToSystem", self, system=newSystemPath)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, "setTerminalServer")

    def setTerminalServer(self, termservername):
        """
        Set the terminal server of this device

        @param termservername: device name of terminal server
        @permission: ZEN_CHANGE_DEVICE
        """
        termserver = self.findDevice(termservername)
        if termserver:
            self.addRelation("termserver", termserver)

    def _setRelations(self, relName, objGetter, relPaths):
        """
        Set related objects to this device

        @param relName: name of the relation to set
        @param objGetter: method to get the relation
        @param relPaths: list of relationship paths
        """
        if not isinstance(relPaths, (list, tuple)):
            relPaths = [
                relPaths,
            ]
        relPaths = filter(lambda x: x.strip(), relPaths)
        rel = getattr(self, relName, None)
        if not rel:
            raise AttributeError("Relation %s not found" % relName)
        curRelIds = {}
        for value in rel.objectValuesAll():
            curRelIds[value.getOrganizerName()] = value
        for path in relPaths:
            if path not in curRelIds:
                robj = objGetter(path)
                self.addRelation(relName, robj)
            else:
                del curRelIds[path]
        for obj in curRelIds.values():
            self.removeRelation(relName, obj)
        self.setAdminLocalRoles()

    def _getOtherExpandedLinks(self):
        """
        @rtype list
        @return a list of the html links supplied by implementers
                of the IExpandedLinkProvider subscriber interface
        """
        providers = subscribers([self], IExpandedLinkProvider)
        expandedLinkList = []
        for provider in providers:
            expandedLinkList.extend(provider.getExpandedLinks())
        return expandedLinkList

    def getExpandedLinks(self):
        """
        Return the expanded zComment property

        @rtype: HTML output
        """
        from Products.ZenUtils.ZenTales import talesEval

        try:
            linksHtml = talesEval("string:" + self.zLinks, self)
            otherLinks = self._getOtherExpandedLinks()
            if otherLinks:
                linksHtml += "<br/>".join(otherLinks)
            return linksHtml
        except Exception as ex:
            import cgi

            return "<i class='errortitle'>%s</i>" % cgi.escape(str(ex))

    ####################################################################
    # Private getter functions that implement DeviceResultInt
    ####################################################################

    security.declareProtected(ZEN_VIEW, "device")

    def device(self):
        """
        Support DeviceResultInt mixin class. Returns itself

        @permission: ZEN_VIEW
        """
        return self

    ####################################################################
    # Status Management Functions used by status monitors
    ####################################################################

    def pastSnmpMaxFailures(self):
        """
        Returns true if the device has more SNMP failures
        than maxFailures on its status mon.

        @rtype: boolean
        """
        statusmon = self.monitors()
        if len(statusmon) > 0:
            statusmon = statusmon[0]
            return statusmon.maxFailures < self.getSnmpStatusNumber()
        return False

    # FIXME: cleanup --force option #2660
    security.declareProtected(
        ZEN_MANAGE_DEVICE_STATUS, "getLastPollSnmpUpTime"
    )

    def getLastPollSnmpUpTime(self):
        """
        Get the value of the snmpUpTime status object

        @permission: ZEN_MANAGE_DEVICE_STATUS
        """
        return self._lastPollSnmpUpTime.getStatus()

    # FIXME: cleanup --force option #2660
    security.declareProtected(
        ZEN_MANAGE_DEVICE_STATUS, "setLastPollSnmpUpTime"
    )

    def setLastPollSnmpUpTime(self, value):
        """
        Set the value of the snmpUpTime status object

        @permission: ZEN_MANAGE_DEVICE_STATUS
        """
        self._lastPollSnmpUpTime.setStatus(value)

    def snmpAgeCheck(self, hours):
        """
        Returns True if SNMP data was collected more than 24 hours ago
        """
        lastcoll = self.getSnmpLastCollection()
        hours = hours / 24.0
        if DateTime() > lastcoll + hours:
            return 1

    security.declareProtected(ZEN_CHANGE_DEVICE, "applyProductContext")

    def applyProductContext(self):
        """
        Apply zProperties inherited from Product Contexts.
        """
        self._applyProdContext(self.hw.getProductContext())
        self._applyProdContext(self.os.getProductContext())
        for soft in self.os.software():
            self._applyProdContext(soft.getProductContext())

    def _applyProdContext(self, context):
        """
        Apply zProperties taken for the product context passed in.

        @param context: list of tuples returned from
        getProductContext on a MEProduct.
        """
        for name, value in context:
            if name == "zDeviceClass" and value:
                log.info("move device to %s", value)
                self.moveDevices(value, self.id)
            elif name == "zDeviceGroup" and value:
                log.info("add device to group %s", value)
                self.addDeviceGroup(value)
            elif name == "zSystem" and value:
                log.info("add device to system %s", value)
                self.addSystem(value)

    ####################################################################
    # Management Functions
    ####################################################################

    security.declareProtected(ZEN_MANAGE_DEVICE, "collectDevice")

    def collectDevice(
        self,
        setlog=True,
        REQUEST=None,
        generateEvents=False,
        background=False,
        write=None,
        debug=False,
    ):
        """
        Collect the configuration of this device AKA Model Device

        @param setlog: If true, set up the output log of this process
        @permission: ZEN_MANAGE_DEVICE
        @todo: generateEvents param is not being used.
        """
        unused(generateEvents)
        xmlrpc = isXmlRpc(REQUEST)
        perfConf = self.getPerformanceServer()
        if perfConf is None:
            msg = (
                "Device %s in unknown state -- remove and remodel"
                % self.titleOrId()
            )
            if write is not None:
                write(msg)
            log.error("Unable to get collector info: %s", msg)
            if xmlrpc:
                return 1
            return

        perfConf.collectDevice(
            self,
            setlog,
            REQUEST,
            generateEvents,
            background,
            write,
            collectPlugins="",
            debug=debug,
        )

        if REQUEST:
            audit("UI.Device.Remodel", self)
        if xmlrpc:
            return 0

    security.declareProtected(ZEN_MANAGE_DEVICE, "runDeviceMonitor")

    def runDeviceMonitor(self, REQUEST=None, write=None, debug=False):
        """
        Run monitoring daemon agains the device ones
        """
        # Daemons to run against the device
        xmlrpc = isXmlRpc(REQUEST)
        perfConf = self.getPerformanceServer()
        if perfConf is None:
            msg = (
                "Device %s in unknown state -- remove and remodel"
                % self.titleOrId()
            )
            if write is not None:
                write(msg)
            log.error("Unable to get collector info: %s", msg)
            if xmlrpc:
                return 1
            return

        # Getting all the datasources from template signed to that
        # device for determining which daemon to run
        templates = self.getRRDTemplates()
        datasources = itertools.chain.from_iterable(
            template.getRRDDataSources() for template in templates
        )
        collection_daemons = set()
        for ds in datasources:
            if isPythonDataSource(ds):
                daemon = _sourcetype_to_collector_map["Python"]
            else:
                daemon = _sourcetype_to_collector_map.get(ds.sourcetype)
            if daemon:
                collection_daemons.add(daemon)

        # We support only core collection daemons
        # zenpython; zenperfsnmp; zencommand
        if not collection_daemons:
            if write:
                write(
                    "Monitoring through UI only support COMMAND, "
                    "SNMP and ZenPython type of datasources"
                )
            if xmlrpc:
                return 1
            return
        # Pass collection_daemons as a list because perfConf.runDeviceMonitor
        # was written expecting that parameter to be a list.
        perfConf.runDeviceMonitor(
            self,
            REQUEST,
            write,
            list(collection_daemons),
            debug=debug,
        )
        if REQUEST:
            audit("UI.Device.Monitor", self)
        if xmlrpc:
            return 0

    security.declareProtected(ZEN_MANAGE_DEVICE, "monitorPerDatasource")

    def monitorPerDatasource(self, dsObj, REQUEST=None, write=None):
        """
        Run monitoring daemon against one device and one datasource ones
        """
        parameter = "--datasource"
        value = "%s/%s" % (dsObj.rrdTemplate.obj.id, dsObj.id)
        if isPythonDataSource(dsObj):
            collection_daemon = _sourcetype_to_collector_map["Python"]
        elif dsObj.sourcetype == "COMMAND":
            collection_daemon = _sourcetype_to_collector_map["COMMAND"]
        elif dsObj.sourcetype == "SNMP":
            collection_daemon = _sourcetype_to_collector_map["SNMP"]
            parameter = "--oid"
            value = dsObj.oid
        else:
            collection_daemon = ""

        xmlrpc = isXmlRpc(REQUEST)
        perfConf = self.getPerformanceServer()
        if not collection_daemon:
            if write:
                write(
                    "Modeling through UI only support COMMAND, "
                    "SNMP and ZenPython type of datasources"
                )
            if xmlrpc:
                return 1
            return

        perfConf.runDeviceMonitorPerDatasource(
            self, REQUEST, write, collection_daemon, parameter, value
        )
        if xmlrpc:
            return 0

    def _removeManageIp(self):
        """
        Safely remove the manageIp object from the device.  Remove the
        ipaddress object from the device:ipaddress relation, and if the
        ipaddress does not have any remaining relations, remove the
        ipaddress object.
        """
        deviceId = self.titleOrId()
        manageIp = self.manageIp
        ipaddr = self.ipaddress()
        log.debug('Set manageIp on {} to empty string'.format(deviceId))
        if ipaddr:
            ipaddrString = ipaddr.id
            log.debug('Removing ipaddress/manageDevice relation from {} to {}'.format(deviceId, str(ipaddr)))
            if ipaddrString != manageIp:
                # Shouldn't happen, but manageIp is not the
                # IP set on the device.
                log.warn('Device {} has a mismatch between manageIp({})'
                              'and device ip ({})'.format(
                                  deviceId, manageIp, ipaddrString
                                  )
                              )
            # Remove the ip from the ipaddress relation on the device
            self.ipaddress.removeRelation(ipaddr)
            # removeIpAddresses will only remove IP addresses that are no longer
            #  attached to any device, so it's safe to call at this point
            netFacade = getFacade('network', self.dmd)
            ips = [ipaddr.getPrimaryId()]
            log.debug('Removing IP address obj {} if no longer used'.format(ipaddrString))
            removeCount, errorCount = netFacade.removeIpAddresses(ips)
            if errorCount:
                # This most likely means that the IP address is still
                # attached to a different device
                log.warn('Could not remove '
                         'IP address {}'.format(ipaddrString))
        # Set the manageIp to blank
        self.manageIp = ''

    security.declareProtected(ZEN_DELETE_DEVICE, "deleteDevice")

    def deleteDevice(
        self,
        deleteStatus=False,
        deleteHistory=False,
        deletePerf=False,
        REQUEST=None,
    ):
        """
        Delete device from the database

        NB: deleteHistory is disabled for the 2.2 release.  In some
        circumstances it was causing many subprocesses to be spawned
        and creating a gridlock situation.

        NOTE: deleteStatus no longer deletes events from the summary
        table, but closes them.

        @permission: ZEN_ADMIN_DEVICE
        """
        parent = self.getPrimaryParent()
        if deleteStatus:
            # Close events for this device
            zep = getFacade("zep")
            tagFilter = {"tag_uuids": [IGlobalIdentifier(self).getGUID()]}
            eventFilter = {"tag_filter": [tagFilter]}
            log.debug("Closing events for device: %s", self.getId())
            zep.closeEventSummaries(eventFilter=eventFilter)
        if REQUEST:
            audit(
                "UI.Device.Delete",
                self,
                deleteStatus=deleteStatus,
                deleteHistory=deleteHistory,
                deletePerf=deletePerf,
            )
        self.getDmdRoot("Monitors").deletePreviousCollectorForDevice(
            self.getId()
        )
        self.dmd.getDmdRoot("ZenLinkManager").remove_device_from_cache(
            self.getId()
        )
        self._removeManageIp()
        parent._delObject(self.getId())
        if REQUEST:
            if parent.getId() == "devices":
                parent = parent.getPrimaryParent()
            REQUEST["RESPONSE"].redirect(
                parent.absolute_url_path() + "/deviceOrganizerStatus"
                "?message=Device deleted"
            )

    security.declareProtected(ZEN_ADMIN_DEVICE, "renameDevice")

    def renameDevice(self, newId=None, REQUEST=None, retainGraphData=False):
        """
        Rename device from the DMD.  Disallow assignment of
        an id that already exists in the system.
        Block renaming for this Device if a rename is already in progress.

        @permission: ZEN_ADMIN_DEVICE
        @param newId: new name
        @type newId: string
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if self.renameInProgress:
            log.warn("Rename already in progress for device %s.", self.id)
            raise Exception(
                "Rename already in progress for device {}.".format(self.id),
            )

        parent = self.getPrimaryParent()
        path = self.absolute_url_path()
        oldId = self.getId()

        if newId is None:
            return path

        if not isinstance(newId, unicode):
            newId = self.prepId(newId)

        newId = newId.strip()

        if newId == "" or newId == oldId:
            return path

        device = self.dmd.Devices.findDeviceByIdExact(newId)
        if device:
            raise DeviceExistsError(
                "Device already exists with id %s" % newId,
                device,
            )

        if REQUEST:
            audit("UI.Device.ChangeId", self, id=newId)

        # side effect: self.getId() will return newId after this call
        try:
            # If there is a title, change the title to the newId
            # (ticket #5443).  manage_renameObject will reindex.
            if self.title:
                self.title = newId
            parent.manage_renameObject(oldId, newId)
            self.setLastChange()

            # Replace the old id in performance data with the new id.
            # See ZEN-27329.
            if retainGraphData:
                self.renameInProgress = True
                self.reassociatePerfDataAfterRename(oldId, newId)

            return self.absolute_url_path()
        except CopyError:
            raise Exception("Device rename failed.")

    def reassociatePerfDataAfterRename(self, oldId, newId):
        """
        Replace a dev id in metric names and tag values with the new id after
        renaming the device.
        """
        self.dmd.JobManager.addJob(
            FacadeMethodJob,
            description=(
                "Reassociating performance data for device {} with "
                "new ID {}".format(oldId, newId)
            ),
            kwargs=dict(
                facadefqdn="Products.Zuul.facades.metricfacade.MetricFacade",
                method="renameDevice",
                oldId=oldId,
                newId=newId,
            ),
        )

    security.declareProtected(ZEN_CHANGE_DEVICE, "index_object")

    @deprecated
    def index_object(self, idxs=None, noips=False):
        """
        Override so ips get indexed on move.  DEPRECATED
        """
        pass

    security.declareProtected(ZEN_CHANGE_DEVICE, "unindex_object")

    @deprecated
    def unindex_object(self):
        """
        Override so ips get unindexed as well.  DEPRECATED
        """
        pass

    def getUserCommandTargets(self):
        """
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        """
        return [self]

    def getUserCommandEnvironment(self):
        """
        Returns the tales environment used to evaluate the command
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update(
            {
                "dev": context,
                "device": context,
            }
        )
        return environ

    def getUrlForUserCommands(self):
        """
        Returns a URL to redirect to after a command has executed
        used by Commandable
        """
        return self.getPrimaryUrlPath() + "/deviceManagement"

    def getHTMLEventSummary(self, severity=4):
        """
        Returns HTML Event Summary of a device
        """
        html = []
        html.append("<table width='100%' cellspacing='1' cellpadding='3'>")
        html.append("<tr>")

        def evsummarycell(ev):
            if ev[1] - ev[2] >= 0:
                klass = "%s empty thin" % ev[0]
            else:
                klass = "%s thin" % ev[0]
            h = '<th align="center" width="16%%" class="%s">%s/%s</th>' % (
                klass,
                ev[1],
                ev[2],
            )
            return h

        info = self.getEventSummary(severity)
        html += map(evsummarycell, info)
        html.append("</tr></table>")
        return "\n".join(html)

    def getDataForJSON(self, minSeverity=0):
        """
        Returns data ready for serialization
        """
        url, classurl = map(
            urlquote, (self.getDeviceUrl(), self.getDeviceClassPath())
        )
        id = '<a class="tablevalues" href="%s">%s</a>' % (
            url,
            self.titleOrId(),
        )
        ip = self.getDeviceIp()
        if self.checkRemotePerm(ZEN_VIEW, self.deviceClass()):
            path = '<a href="/zport/dmd/Devices%s">%s</a>' % (
                classurl,
                classurl,
            )
        else:
            path = classurl
        prod = self.getProdState()
        evsum = getEventPillME(self, 1, minSeverity)[0]
        return [id, ip, path, prod, evsum, self.id]

    def exportXmlHook(self, ofile, ignorerels):
        """
        Add export of our child objects.
        """
        map(lambda o: o.exportXml(ofile, ignorerels), (self.hw, self.os))

    security.declareProtected(ZEN_MANAGE_DEVICE, "pushConfig")

    def pushConfig(self, REQUEST=None):
        """
        This will result in a push of all the devices to live collectors

        @permission: ZEN_MANAGE_DEVICE
        """
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Changes Pushed",
                "Changes to %s pushed to collectors." % self.id,
            )
            audit("UI.Device.PushChanges", self)
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES, "bindTemplates")

    def bindTemplates(self, ids=(), REQUEST=None):
        """
        This will bind available templates to the zDeviceTemplates

        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        result = self.setZenProperty("zDeviceTemplates", ids, REQUEST)
        if REQUEST:
            audit("UI.Device.BindTemplates", self, templates=ids)
        return result

    security.declareProtected(
        ZEN_EDIT_LOCAL_TEMPLATES, "removeZDeviceTemplates"
    )

    def removeZDeviceTemplates(self, REQUEST=None):
        """
        Deletes the local zProperty, zDeviceTemplates

        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        for id in self.zDeviceTemplates:
            self.removeLocalRRDTemplate(id)
            if REQUEST:
                audit("UI.Device.RemoveLocalTemplate", self, template=id)
        from Products.ZenRelations.ZenPropertyManager import (
            ZenPropertyDoesNotExist,
        )

        try:
            return self.deleteZenProperty("zDeviceTemplates", REQUEST)
        except ZenPropertyDoesNotExist:
            if REQUEST:
                return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES, "addLocalTemplate")

    def addLocalTemplate(self, id, REQUEST=None):
        """
        Create a local template on a device

        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        from Products.ZenModel.RRDTemplate import manage_addRRDTemplate

        manage_addRRDTemplate(self, id)
        if (
            id not in self.zDeviceTemplates
            and not id.endswith("-replacement")
            and not id.endswith("-addition")
        ):
            self.bindTemplates(self.zDeviceTemplates + [id])
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Local Template Added",
                "Added template %s to %s." % (id, self.id),
            )
            audit("UI.Device.AddLocalTemplate", self, template=id)
            return self.callZenScreen(REQUEST)

    def getAvailableTemplates(self):
        """
        Returns all available templates for this device
        """
        # All templates defined on this device are available
        templates = self.objectValues("RRDTemplate")
        # Any templates available to the class that aren't overridden locally
        # are also available
        device_template_ids = set(t.id for t in templates)
        templates.extend(
            t
            for t in self.deviceClass().getRRDTemplates()
            if t.id not in device_template_ids
        )
        # Filter out any templates that have been 'replaced'
        filteredTemplates = list(templates)
        for t in templates:
            tName = t.titleOrId()
            if tName.endswith("-replacement") or tName.endswith("-addition"):
                filteredTemplates.remove(t)
        # filter for python class before sorting
        templates = filter(
            lambda t: isinstance(self, t.getTargetPythonClass()),
            filteredTemplates,
        )
        return sorted(templates, key=lambda x: x.id.lower())

    def getSnmpV3EngineId(self):
        return self.getProperty("zSnmpEngineId")

    def setSnmpV3EngineId(self, value):
        self.setZenProperty("zSnmpEngineId", value)

    security.declareProtected(ZEN_VIEW, "getLinks")

    def getLinks(self, OSI_layer="3"):
        """
        Returns all Links on this Device's interfaces

        @permission: ZEN_VIEW
        """
        if OSI_layer == "3":
            from Products.ZenUtils.NetworkTree import getDeviceNetworkLinks

            for link in getDeviceNetworkLinks(self):
                yield link
        else:
            for iface in self.os.interfaces.objectValuesGen():
                for link in iface.links.objectValuesGen():
                    yield link

    security.declareProtected(ZEN_VIEW, "getXMLEdges")

    def getXMLEdges(self, depth=3, filter="/", start=()):
        """
        Gets XML
        """
        if not start:
            start = self.id
        edges = NetworkTree.get_edges(
            self, depth, withIcons=True, filter=filter
        )
        return edgesToXML(edges, start)

    security.declareProtected(ZEN_VIEW, "getPrettyLink")

    @unpublished
    def getPrettyLink(self, target=None, altHref=""):
        """
        Gets a link to this device, plus an icon

        @rtype: HTML text
        @permission: ZEN_VIEW
        """
        template = (
            "<div class='device-icon-container'>"
            "<img class='device-icon' src='%s'/> "
            "</div>%s"
        )
        icon = self.getIconPath()
        href = altHref if altHref else self.getPrimaryUrlPath()
        name = self.titleOrId()

        rendered = template % (icon, cgi.escape(name))

        if not self.checkRemotePerm(ZEN_VIEW, self):
            return rendered
        else:
            return "<a %s href='%s' class='prettylink'>%s</a>" % (
                "target=" + target if target else "",
                href,
                rendered,
            )

    def osProcessClassMatchData(self):
        """
        Get a list of dictionaries containing everything needed to match
        processes against the global list of process classes.
        """
        matchers = []
        for pc in self.getDmdRoot("Processes").getSubOSProcessClassesSorted():
            matchers.append(
                {
                    "includeRegex": pc.includeRegex,
                    "excludeRegex": pc.excludeRegex,
                    "replaceRegex": pc.replaceRegex,
                    "replacement": pc.replacement,
                    "primaryUrlPath": pc.getPrimaryUrlPath(),
                    "primaryDmdId": pc.getPrimaryDmdId(),
                }
            )

        return matchers

    def manageIpVersion(self):
        """
        Returns either 4 or 6 depending on the version
        of the manageIp ip adddress
        """
        from ipaddr import IPAddress

        try:
            ip = self.getManageIp()
            return IPAddress(ip).version
        except ValueError:
            # could not parse the ip address
            pass
        # if we can't parse it assume it is ipv4
        return 4

    def snmpwalkPrefix(self):
        """
        This method gets the ip address prefix used for this device
        when running snmpwalk.

        @rtype:   string
        @return:  Prefix used for snmwalk for this device
        """
        if self.manageIpVersion() == 6:
            return "udp6:"
        return ""

    def pingCommand(self):
        """
        Used by the user commands this returns which ping command
        this device should use.
        @rtype: string
        @return "ping" or "ping6" depending on if the manageIp is ipv6 or not
        """
        if self.manageIpVersion() == 6:
            return "ping6"
        return "ping"

    def tracerouteCommand(self):
        """
        Used by the user commands this returns which traceroute command
        this device should use.
        @rtype: string
        @return "traceroute" or "traceroute6" depending on if the
            manageIp is ipv6 or not.
        """
        if self.manageIpVersion() == 6:
            return "traceroute6"
        return "traceroute"

    def getStatus(self, statusclass=None, **kwargs):
        """
        Return the status number for this device of class statClass.
        If statusclass not set, search by zStatusEventClass.
        """
        if not self.monitorDevice():
            return None

        if statusclass is None:
            statusclass = self.zStatusEventClass
            zep = getFacade("zep", self)
            try:
                event_filter = zep.createEventFilter(
                    tags=[self.getUUID()],
                    element_sub_identifier=[""],
                    severity=[SEVERITY_CRITICAL],
                    status=[
                        STATUS_NEW,
                        STATUS_ACKNOWLEDGED,
                        STATUS_SUPPRESSED,
                    ],
                    event_class=filter(None, [self.zStatusEventClass]),
                )

                result = zep.getEventSummaries(0, filter=event_filter, limit=0)
                return int(result["total"])
            except Exception:
                return None

        if statusclass == Status_Ping:
            return self._getPingStatus(statusclass)

        return super(Device, self).getStatus(statusclass, **kwargs)

    def _getPingStatus(self, statusclass):
        if not self.zPingMonitorIgnore and self.getManageIp():
            # Override normal behavior - we only care if the manage IP is down

            # Need to add the ipinterface component id to search since we may
            # be pinging interfaces and only care about status of the one that
            # matches the manage ip.  This is potentially expensive
            element_sub_identifier = [""]
            ifaces = self.getDeviceComponents(type="IpInterface")
            for iface in ifaces:
                if self.manageIp in [
                    ip.partition("/")[0] for ip in iface.getIpAddresses()
                ]:
                    element_sub_identifier.append(iface.id)
                    break

            zep = getFacade("zep", self)
            event_filter = zep.createEventFilter(
                tags=[self.getUUID()],
                severity=[SEVERITY_WARNING, SEVERITY_ERROR, SEVERITY_CRITICAL],
                status=[STATUS_NEW, STATUS_ACKNOWLEDGED, STATUS_SUPPRESSED],
                element_sub_identifier=element_sub_identifier,
                event_class=filter(None, [statusclass]),
                details={
                    EventProxy.DEVICE_IP_ADDRESS_DETAIL_KEY: self.getManageIp()
                },
            )
            result = zep.getEventSummaries(0, filter=event_filter, limit=0)
            return int(result["total"])
        else:
            return None

    def ipAddressAsInt(self):
        ip = self.getManageIp()
        if ip:
            ip = ip.partition("/")[0]
        if ip:
            return str(numbip(ip))

    def getMacAddressCache(self):
        if self.macaddresses is None:
            self.macaddresses = OOSet()

        return self.macaddresses

    def getMacAddresses(self):
        return list(self.macaddresses or [])


InitializeClass(Device)
