##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

import pkg_resources

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from Acquisition import aq_base, aq_chain
from App.special_dtml import DTMLFile
from OFS.PropertyManager import PropertyManager
from zExceptions import BadRequest
from ZPublisher.Converters import type_converters

from Products.ZenMessaging.audit import audit
from Products.ZenModel.ZenossSecurity import (
    ZEN_ZPROPERTIES_EDIT,
    ZEN_ZPROPERTIES_VIEW,
)
from Products.ZenUtils.snmp import authentication_protocols, privacy_protocols
from Products.ZenUtils.Utils import unused, getDisplayType
from Products.ZenWidgets.interfaces import IMessageSender

from .Exceptions import zenmarker
from .zPropertyCategory import (
    getzPropertyCategory,
    setzPropertyCategory,
)

iszprop = re.compile("z[A-Z]").match
iscustprop = re.compile("c[A-Z]").match

log = logging.getLogger("zen.PropertyManager")

Z_PROPERTY_META_DATA = {}
# Z_PROPERTIES is a list of (id, value, type, name, description) tuples that
# define all the zProperties.  The values are set on dmd.Devices in the
# buildDeviceTreeProperties of DeviceClass
Z_PROPERTIES = [
    # Config Cache properties
    (
        "zDeviceConfigBuildTimeout",
        7200,
        "int",
        "Device configuration build timeout",
        "The number of seconds before timing out a device configuration build."
    ),
    (
        "zDeviceConfigPendingTimeout",
        7200,
        "int",
        "Device configuration build queued timeout",
        "The number of seconds a device configuration build may be queued "
        "before a timeout."
    ),
    (
        "zDeviceConfigTTL",
        43200,
        "int",
        "Device configuration expiration",
        "The maximum number of seconds to wait before rebuilding a "
        "device configuration."
    ),
    (
        "zDeviceConfigMinimumTTL",
        0,
        "int",
        "Device configuration pre-expiration window",
        "The number of seconds the configuration is protected "
        "from being rebuilt."
    ),
    # zPythonClass maps device class to python classs (separate from device
    # class name)
    (
        "zPythonClass",
        "",
        "string",
        "Python Class",
        "Python module used when creating a new device instances.",
    ),
    # zProdStateThreshold is the production state threshold at which to start
    # monitoring boxes
    (
        "zProdStateThreshold",
        300,
        "int",
        "Production State Threshold",
        "Production state threshold at which to start monitoring boxes.",
    ),
    # zIfDescription determines whether or not the ifdescripion field is
    # displayed
    (
        "zIfDescription",
        False,
        "boolean",
        "If Description",
        "Shows the interface description field in the interface list.",
    ),
    # Snmp collection properties
    (
        "zSnmpCommunities",
        ["public", "private"],
        "lines",
        "SNMP Communities",
        "Array of SNMP community strings that ZenModeler uses when "
        "collecting SNMP information. When you set this property, "
        "communities are tried in order; the first in the list that is "
        "successful is used as zSnmpCommunity. If none is successful, "
        "then the current value of zSnmpCommunity is used. The default "
        'value for the entire system is "public."',
    ),
    (
        "zSnmpCommunity",
        "public",
        "string",
        "SNMP Community String",
        "Community string to be used when collecting SNMP information. "
        "If it is different than what is found by ZenModeler, it will be "
        "set on the modeled device.",
    ),
    (
        "zSnmpPort",
        161,
        "int",
        "SNMP Port",
        "Port that the SNMP agent listens on.",
    ),
    (
        "zSnmpVer",
        "v2c",
        "string",
        "SNMP Version",
        "SNMP version used. Valid values are v1, v2c, v3.",
    ),
    (
        "zSnmpTries",
        6,
        "int",
        "SNMP Tries",
        "Amount of tries to collect SNMP data",
    ),
    (
        "zSnmpTimeout",
        1,
        "float",
        "SNMP Timeout",
        "Timeout time in seconds for an SNMP request",
    ),
    (
        "zSnmpEngineId",
        "",
        "string",
        "SNMP Engine ID",
        "Engine ID is the administratively unique identifier for the "
        "SNMPv3 engine",
    ),
    (
        "zSnmpSecurityName",
        "",
        "string",
        "SNMP Security Name",
        "The Security Name (user) to use when making SNMPv3 requests.",
    ),
    (
        "zSnmpAuthPassword",
        "",
        "password",
        "SNMP Auth Password",
        "The shared private key used for authentication. "
        "Must be at least 8 characters long.",
    ),
    (
        "zSnmpPrivPassword",
        "",
        "password",
        "SNMP Private Password",
        "The shared private key used for encrypting SNMP requests. "
        "Must be at least 8 characters long.",
    ),
    (
        "zSnmpAuthType",
        "",
        "string",
        "SNMP Authentication Protocol",
        'The cryptographic protocol used to authenticate SNMP requests.',
    ),
    (
        "zSnmpPrivType",
        "",
        "string",
        "SNMP Privacy Protocol",
        'The cryptographic protocol used to encrypt SNMP packets.',
    ),
    (
        "zSnmpContext",
        "",
        "string",
        "SNMP Context",
        "Defines the SNMPv3 CONTEXT specified by the -n flag",
    ),
    (
        "zSnmpCollectionInterval",
        300,
        "int",
        "SNMP Collection Interval",
        "Defines, in seconds, how often the system collects "
        "performance information for each device.",
    ),
    (
        "zRouteMapCollectOnlyLocal",
        False,
        "boolean",
        "Router Map Collect Only (Local)",
        "Only collect local routes. (These usually are manually "
        "configured rather than learned through a routing protocol.)",
    ),
    (
        "zRouteMapCollectOnlyIndirect",
        False,
        "boolean",
        "Route Map Collect Only (Indirect)",
        "Only collect routes that are directly connected to the device.",
    ),
    (
        "zRouteMapMaxRoutes",
        500,
        "int",
        "Route Map Max Routes",
        "Maximum number of routes to model.",
    ),
    (
        "zInterfaceMapIgnoreTypes",
        "",
        "string",
        "Interface Map Ignore Types",
        "Filters out interface maps that should not be discovered.",
    ),
    (
        "zInterfaceMapIgnoreNames",
        "",
        "string",
        "Interface Map Ignore Names",
        "Filters out interfaces that should not be discovered.",
    ),
    (
        "zInterfaceMapIgnoreDescriptions",
        "",
        "string",
        "Interface Map Ignore Description",
        "Filters out interfaces based on description.",
    ),
    (
        "zFileSystemMapIgnoreTypes",
        [],
        "lines",
        "File System Map Ignore Types",
        "Do not use.",
    ),
    (
        "zFileSystemMapIgnoreNames",
        "",
        "string",
        "File System Map Ignore Names",
        "Sets a regular expression of file system names to ignore.",
    ),
    (
        "zFileSystemSizeOffset",
        1.0,
        "float",
        "File System Size Offset",
        "SNMP typically reports the total space available to privileged "
        "users. Resource Manager (like the df command) reports capacity "
        "based on the space available to non-privileged users. The value "
        "of zFileSystemSizeOffset should be the fraction of the total "
        "space that is available to non-privileged users. The default "
        "reserved value is 5% of total space, so zFileSystemSizeOffset is "
        "preset to .95. If the reserved portion is different than 5%, then "
        "adjust the value of zFileSystemSizeOffset accordingly. The "
        "fraction should be set according to the value "
        "( Used + Avail ) / Size when the df -PkH command is run at the "
        "command line.",
    ),
    (
        "zHardDiskMapMatch",
        "",
        "string",
        "Hard Disk Map Match",
        "Regular expression that uses the disk ID in the diskstats output "
        "to filter disk activity statistics for inclusion in performance "
        "monitoring.",
    ),
    (
        "zSysedgeDiskMapIgnoreNames",
        "",
        "string",
        "Sysedge Disk Map Ignore Names",
        "",
    ),
    (
        "zIpServiceMapMaxPort",
        1024,
        "int",
        "IP Service Map Max Port",
        "Specifies the highest port to scan. The default is 1024.",
    ),
    (
        "zDeviceTemplates",
        ["Device"],
        "lines",
        "Device Templates",
        "Sets the templates associated with this device. Linked by name.",
    ),
    (
        "zLocalIpAddresses",
        "^127|^0\\.0|^169\\.254|^224|^fe80::",
        "string",
        "Local IP Addresses",
        "",
    ),
    (
        "zLocalInterfaceNames",
        "^lo|^vmnet",
        "string",
        "Local Interface Names",
        "Regular expression that uses interface name to determine whether "
        "the IP addresses on an interface should be incorporated into the "
        'network map. For instance, a loopback interface "lo" might be '
        "excluded.",
    ),
    # Status monitor properties
    (
        "zSnmpMonitorIgnore",
        False,
        "boolean",
        "Ignore SNMP Monitor?",
        "Whether or not to ignore monitoring SNMP on a device.",
    ),
    (
        "zPingMonitorIgnore",
        False,
        "boolean",
        "Ignore Ping Monitor?",
        "Whether or not to ping the device.",
    ),
    (
        "zStatusConnectTimeout",
        15.0,
        "float",
        "Status Connection Timeout (seconds)",
        "The amount of time that the zenstatus daemon should wait before "
        "marking an IP service down.",
    ),
    (
        "zStatusEventClass",
        "/Status/",
        "string",
        "Event class that affect status",
        "Event class that mark device Down if we got critical event",
    ),
    # DataCollector properties
    ("zCollectorPlugins", [], "lines", "Collector Plugins", ""),
    (
        "zCollectorClientTimeout",
        180,
        "int",
        "Collector Client Timeout (seconds)",
        "Allows you to set the timeout time of the collector client in "
        "seconds",
    ),
    (
        "zCollectorDecoding",
        "utf-8",
        "string",
        "Collector Decoding",
        "Converts incoming characters to Unicode.",
    ),
    (
        "zCommandUsername",
        "",
        "string",
        "Username",
        "Specifies the user name to use when performing command collection "
        "and SSH.",
    ),
    (
        "zCommandPassword",
        "",
        "password",
        "Password",
        "Specifies the password to use when performing command logins "
        "and SSH.",
    ),
    (
        "zCommandProtocol",
        "ssh",
        "string",
        "Command Protocol",
        "Establishes the protocol to use when performing command "
        "collection. Possible values are SSH and telnet.",
    ),
    (
        "zCommandPort",
        22,
        "int",
        "Command Port",
        "Specifies the port to connect to when performing command collection.",
    ),
    (
        "zCommandLoginTries",
        1,
        "int",
        "Command Login Tries",
        "Sets the number of times to attempt login.",
    ),
    (
        "zCommandLoginTimeout",
        10.0,
        "float",
        "Timeout for Login (seconds)",
        "Specifies the time to wait for a login prompt.",
    ),
    (
        "zCommandCommandTimeout",
        10.0,
        "float",
        "Timeout for Commands (seconds)",
        "Specifies the time to wait for a command to complete.",
    ),
    (
        "zCommandUserCommandTimeout",
        15.0,
        "float",
        "Timeout for User Commands (seconds)",
        "Specifies the time to wait for a user command to complete.",
    ),
    (
        "zCommandSearchPath",
        [],
        "lines",
        "Command Search Path",
        "Sets the path to search for any commands.",
    ),
    (
        "zCommandExistanceTest",
        "test -f %s",
        "string",
        "Command Existance Test",
        "",
    ),
    (
        "zCommandPath",
        "/usr/local/zenoss/libexec",
        "string",
        "Command Path",
        "Sets the default path where ZenCommand plug-ins are installed on "
        "the local Resource Manager box (or on a remote box where SSH is "
        "used to run the command).",
    ),
    (
        "zCommandCollectionInterval",
        300,
        "int",
        "Command Collection Interval",
        "Defines, in seconds, the default collection interval for "
        "command datasources.",
    ),
    (
        "zTelnetLoginRegex",
        "ogin:.$",
        "string",
        "Telnet Login",
        "Regular expression to match the login prompt.",
    ),
    (
        "zTelnetPasswordRegex",
        "assword:",
        "string",
        "Telnet Password Regex",
        "Regular expression to match the password prompt.",
    ),
    (
        "zTelnetSuccessRegexList",
        ["\\$.$", "\\#.$"],
        "lines",
        "Telnet Success Regex",
        "List of regular expressions to match the command prompt.",
    ),
    (
        "zTelnetEnable",
        False,
        "boolean",
        "Enable Telnet?",
        "When logging into a Cisco device issue the enable command to "
        "enable access during command collection.",
    ),
    (
        "zTelnetEnableRegex",
        "assword:",
        "string",
        "Telnet Enable Regex",
        "Regular expression to match the enable prompt.",
    ),
    (
        "zTelnetTermLength",
        True,
        "boolean",
        "Telnet Term Length",
        "On a Cisco device, set term length to Zero.",
    ),
    (
        "zTelnetPromptTimeout",
        10.0,
        "float",
        "Telnet Prompt Timeout (seconds)",
        "Time to wait for the telnet prompt to return.",
    ),
    (
        "zKeyPath",
        "~/.ssh/id_dsa",
        "string",
        "Key Path",
        "Sets the path to the SSH key for device access.",
    ),
    (
        "zMaxOIDPerRequest",
        40,
        "int",
        "Max OID Per Request",
        "Sets the maximum number of OIDs to be sent by the SNMP collection "
        "daemons when querying information. Some devices have small buffers "
        "for handling this information so the number should be lowered.",
    ),
    # Extra stuff for users
    (
        "zLinks",
        "",
        "string",
        "Links",
        "Specifies a place to enter any links associated with the device.",
    ),
    # zIcon is the icon path
    (
        "zIcon",
        "/zport/dmd/img/icons/noicon.png",
        "string",
        "Icon Path",
        "Specifies the icon to represent the device wherever device icon is "
        "shown, such as on the network map and device status page.",
    ),
    # used in ApplyDataMap
    (
        "zCollectorLogChanges",
        True,
        "boolean",
        "Log Collector Changes?",
        "Indicates whether to log changes.",
    ),
    # enable password for Cisco routers
    (
        "zEnablePassword",
        "",
        "password",
        "Enable Password",
        "Enable password for Cisco routers",
    ),
    # used in zenoss.nmap.IpServiceMap
    (
        "zNmapPortscanOptions",
        "-p 1-1024 -sT -oG -",
        "string",
        "Nmap Port Scan Options",
        "Options used on nmap when scanning ports. Used in IpServiceMap",
    ),
    # how many SSH sessions to open up to one device
    # (some SSH servers have a limit)
    (
        "zSshConcurrentSessions",
        10,
        "int",
        "SSH Concurrent Sessions",
        "How many SSH sessions to open up to one device "
        "(some SSH servers have a limit)",
    ),
    (
        "zCredentialsZProperties",
        [],
        "lines",
        "Connection Information",
        "Used by ZenPack authors to denote which zProperties comprise "
        "the credentials for this device class.",
    ),
    (
        "zNoRelationshipCopy",
        ["pack"],
        "lines",
        "Relations to skip during copying",
        "Determine which relations should not being built during copying."
    )

]


class PropertyDescriptor(object):
    """
    Transforms the property value based on its type.

    Follows the Descriptor protocol defined at
    http://docs.python.org/reference/datamodel.html#descriptors
    """

    def __init__(self, id, type, transformer):
        self.id = id
        self.type = type
        self.transformer = transformer
        # look up the label and description
        self.label = ""
        self.description = ""
        if Z_PROPERTY_META_DATA.get(id):
            self.label = Z_PROPERTY_META_DATA[id].get("label")
            self.description = Z_PROPERTY_META_DATA[id].get("description")

    def __get__(self, instance, owner):
        """
        Returns self for class attribute access.  Returns the transformed
        value for instance attribute access.
        """
        try:
            if instance is None:
                retval = self
            else:
                self._migrate(instance)
                value = instance._propertyValues[self.id]
                retval = self._transform(instance, value, "transformForGet")
            return retval
        except Exception:
            raise AttributeError

    def __set__(self, instance, value):
        """
        Transforms the value and sets it.
        """
        self._migrate(instance)
        self._set(instance, value)

    def __delete__(self, instance):
        """
        Delete the property.
        """
        self._migrate(instance)
        del instance._propertyValues[self.id]

    def _migrate(self, instance):
        """
        If the id is in __dict__ then move the value to the _propertyValues
        dictionary. Check to make sure that the type of this descriptor class
        and the type in the Zope OFS PropertyManager metadata are the same.
        """
        if not hasattr(instance, "_propertyValues"):
            instance._propertyValues = {}
        if self.id in vars(instance):
            self._set(instance, vars(instance)[self.id])
            del instance.__dict__[self.id]
            instance._p_changed = True
        for dct in instance._properties:
            if dct["id"] == self.id:
                if dct["type"] != self.type:
                    dct["type"] = self.type
                    instance._p_changed = True
                if dct.get("label") != self.label:
                    dct["label"] = self.label
                    instance._p_changed = True
                if dct.get("description") != self.description:
                    dct["description"] = self.description
                    instance._p_changed = True
                break

    def _set(self, instance, value):
        """
        Transform and set the value in the _propertyValues dictionary.
        """
        valueToSet = self._transform(instance, value, "transformForSet")
        instance._propertyValues[self.id] = valueToSet

    def _transform(self, instance, value, method):
        """
        Lookup the transformer for the type and transform the value. The
        method parameter can be 'transformForGet' or 'transformForSet' and
        determines the transformer method that is called.
        """
        return getattr(self.transformer, method)(value)


class ZenPropertyDoesNotExist(ValueError):
    pass


class ZenPropertyManager(object, PropertyManager):
    """
    ZenPropertyManager adds keyedselection type to PropertyManager.
    A keyedselection displays a different name in the popup than
    the actual value the popup will have.

    It also has management for zenProperties which are properties that can be
    inherited along the acquisition chain.  All properties are for a branch
    are defined on a "root node" specified by the function which must be
    returned by the function getZenRootNode that should be over ridden in a
    sub class. Properties can then be added further "down" the aq_chain by
    calling setZenProperty on any contained node.

    ZenProperties all have the same prefix which is defined by iszprop
    this can be overridden in a subclass.

    ZenPropertyManager overrides getProperty and getPropertyType from
    PropertyManager to support acquisition. If you want to query an object
    about a property, but do not want it to search the acquisition chain then
    use the super classes method or aq_base.  Example:

        # acquires property from dmd.Devices
        dmd.Devices.Server.getProperty('zCollectorPlugins')

        # does not acquire property from dmd.Devices
        PropertyManager.getProperty(dmd.Devices.Server, 'zCollectorPlugins')

        # also does not acquire property from dmd.Devices
        aq_base(dmd.Devices.Server).getProperty('zSnmpCommunity')

    The properties are stored as attributes which is convenient, but can be
    confusing.  Attribute access always uses acquisition.  Setting an
    attribute, will not add it to the list of properties, so subsquent calls
    to hasProperty or getProperty won't return it.

    Property Transformers are stored at dmd.propertyTransformers and transform
    the property based on type during calls to the _setProperty,
    _updateProperty, and getProperty methods. Adding a property using
    _setProperty applies the appropriate transformer and adds its value as an
    attribute, but when you access it as an attribute the property transformer
    is again applied, but this time using its transformForGet method.
    """

    security = ClassSecurityInfo()

    manage_propertiesForm = DTMLFile(
        "dtml/properties", globals(), property_extensible_schema__=1
    )

    def _setPropValue(self, id, value):
        """Override from PerpertyManager to handle checks and ip creation."""
        self._wrapperCheck(value)
        propType = self.getPropertyType(id)
        if propType == "keyedselection":
            value = int(value)
        if not getattr(self, "_v_propdict", False):
            self._v_propdict = self.propdict()
        if "setter" in self._v_propdict:
            settername = self._v_propdict["setter"]
            setter = getattr(aq_base(self), settername, None)
            if not setter:
                raise ValueError(
                    "setter %s for property %s doesn't exist"
                    % (settername, id)
                )
            if not callable(setter):
                raise TypeError(
                    "setter %s for property %s not callable" % (settername, id)
                )
            setter(value)
        else:
            setattr(self, id, value)

    def _setProperty(
        self,
        id,
        value,
        type="string",
        label=None,
        visible=True,
        setter=None,
        description=None,
    ):
        """For selection and multiple selection properties the value
        argument indicates the select variable of the property.
        """
        self._wrapperCheck(value)
        if not self.valid_property_id(id):
            raise BadRequest("Id %s is invalid or duplicate" % id)

        def setprops(**pschema):
            if setter:
                pschema["setter"] = setter
            if label:
                pschema["label"] = label
            if description:
                pschema["description"] = description
            self._properties = self._properties + (pschema,)

        if type in ("selection", "multiple selection"):

            # NOTE: Moved `import messaging` here to lazify code and
            # remove circular import.
            from Products.ZenWidgets import messaging

            if not hasattr(self, value):
                IMessageSender(self).sendToBrowser(
                    "Selection variable '%s' not found" % value,
                    priority=messaging.WARNING,
                )
                return

            # NOTE: When creating selection properties, specify the name of
            # another property as the Value. This property should return a list
            # of strings will be used to provide choices for the selection.
            select_values = getattr(self, value)
            if not (
                isinstance(select_values, (list, tuple))
                and all(isinstance(v, basestring) for v in select_values)
            ):
                IMessageSender(self).sendToBrowser(
                    "Selection variable '%s' must be a LINES type" % value,
                    priority=messaging.WARNING,
                )
                return

            setprops(id=id, type=type, visible=visible, select_variable=value)
            self._setPropValue(id, "" if (type == "selection") else [])
        else:
            setprops(id=id, type=type, visible=visible)
            self._setPropValue(id, value)

    _onlystars = re.compile(r"^\*+$").search

    def _updateProperty(self, id, value):
        """This method sets a property on a zope object. It overrides the
        method in PropertyManager. If Zope is upgraded you will need to check
        that this method has not changed! It is overridden so that we can catch
        the ValueError returned from the field2* converters in the class
        Converters.py
        """
        try:
            # Do not update property if its a password
            # and value is secured(equals to all asterisk)
            if self.zenPropIsPassword(id) and self._onlystars(value):
                return
            super(ZenPropertyManager, self)._updateProperty(id, value)
        except ValueError:
            proptype = self.getPropertyType(id)
            log.error(
                "Error Saving Property '%s'. New value '%s' is of invalid "
                "type. It should be type '%s'.",
                id,
                value,
                proptype,
            )

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, "manage_editProperties")

    def manage_editProperties(self, REQUEST):
        """Edit object properties via the web.
        The purpose of this method is to change all property values,
        even those not listed in REQUEST; otherwise checkboxes that
        get turned off will be ignored.  Use manage_changeProperties()
        instead for most situations.
        """
        for prop in self._propertyMap():
            name = prop["id"]
            if "w" in prop.get("mode", "wd"):
                value = REQUEST.get(name, "")
                if self.zenPropIsPassword(name) and self._onlystars(value):
                    continue
                self._updateProperty(name, value)
        if getattr(self, "index_object", False):
            self.index_object()
        if REQUEST:
            return self.manage_propertiesForm(
                self, REQUEST, manage_tabs_message="Saved changes."
            )

    def getZenRootNode(self):
        """Sub class must implement to use zenProperties."""
        raise NotImplementedError

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyIds")

    def zenPropertyIds(self, all=True, pfilt=iszprop):
        """Return list of device tree property names.
        If all use list from property root node.
        """
        if all:
            rootnode = self.getZenRootNode()
        else:
            if self.id == self.dmdRootName:
                return []
            rootnode = aq_base(self)
        return sorted(prop for prop in rootnode.propertyIds() if pfilt(prop))

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyItems")

    def zenPropertyItems(self):
        """Return list of (id, value) tuples of zenProperties."""
        return map(lambda x: (x, getattr(self, x)), self.zenPropertyIds())

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyMap")

    def zenPropertyMap(self, pfilt=iszprop):
        """Return property mapping of device tree properties."""
        rootnode = self.getZenRootNode()
        return sorted(
            (pdict for pdict in rootnode.propertyMap() if pfilt(pdict["id"])),
            key=lambda x: x["id"],
        )

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyString")

    def zenPropertyString(self, id):
        """Return the value of a device tree property as a string."""

        def displayLines(lines):
            return "\n".join(str(line) for line in lines)

        def displayPassword(password):
            return "*" * len(password)

        def displayOthers(other):
            return other

        displayFunctions = {"lines": displayLines, "password": displayPassword}
        display = displayFunctions.get(self.getPropertyType(id), displayOthers)
        return display(self.getProperty(id, ""))

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropIsPassword")

    def zenPropIsPassword(self, id):
        """Is this field a password field."""
        passwordTypes = [
            "password",
            "passwd",
            "multilinecredentials",
            "instancecredentials",
        ]
        return self.getPropertyType(id) in passwordTypes

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyPath")

    def zenPropertyPath(self, id):
        """Return the primaryId of where a device tree property is found."""
        ob = self._findParentWithProperty(id)
        if ob is None:
            path = None
        else:
            path = ob.getPrimaryId(self.getZenRootNode().getId())
        return path

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, "setZenProperty")

    def setZenProperty(self, propname, propvalue, REQUEST=None):
        """Add or set the propvalue of the property propname on this node of
        the device Class tree.
        """
        ptype = self.getPropertyType(propname)
        if ptype == "lines":
            dedupedList = []
            for x in propvalue:
                if x not in dedupedList:
                    dedupedList.append(x)
            propvalue = dedupedList
        if getattr(aq_base(self), propname, zenmarker) != zenmarker:
            self._updateProperty(propname, propvalue)
        else:
            if ptype in ("selection", "multiple selection"):
                ptype = "string"
            if ptype in type_converters:
                propvalue = type_converters[ptype](propvalue)
            if ptype == "password" and propvalue == self.zenPropertyString(
                propname
            ):
                # Don't save passwords that haven't changed
                # and don't save "*" passwords
                pass
            elif getattr(self, propname, None) != propvalue:
                self._setProperty(propname, propvalue, type=ptype)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, "saveZenProperties")

    def saveZenProperties(self, pfilt=iszprop, REQUEST=None):
        """Save all ZenProperties found in the REQUEST.form object."""
        oldValues = {}
        newValues = {}
        maskFields = []
        for name, value in REQUEST.form.items():
            if pfilt(name):
                if self.zenPropIsPassword(name):
                    maskFields.append(name)
                    if self._onlystars(value):
                        continue
                oldValues[name] = self.getProperty(name)
                if name == "zCollectorPlugins":
                    if tuple(getattr(self, name, ())) != tuple(value):
                        self.setZenProperty(name, value)
                else:
                    self.setZenProperty(name, value)
                newValues[name] = self.getProperty(name)

        if REQUEST:
            audit(
                ("UI", getDisplayType(self), "EditProperties"),
                self,
                data_=newValues,
                oldData_=oldValues,
                maskFields_=maskFields,
            )
            IMessageSender(self).sendToBrowser(
                "Configuration Propeties Updated",
                "Configuration properties have been updated.",
            )

        return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_EDIT, "deleteZenProperty")

    def deleteZenProperty(self, propname=None, REQUEST=None):
        """
        Delete device tree properties from the this DeviceClass object.
        """
        if propname:
            try:
                self._delProperty(propname)
            except AttributeError:
                # Occasional object corruption where the propName is in
                # _properties but not set as an attribute. filter out the prop
                # and create a new _properties tuple
                newProps = [x for x in self._properties if x["id"] != propname]
                self._properties = tuple(newProps)
            except ValueError:
                raise ZenPropertyDoesNotExist()
        if REQUEST:
            if propname:
                audit(
                    ("UI", getDisplayType(self), "DeleteZProperty"),
                    self,
                    property=propname,
                )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "zenPropertyOptions")

    def zenPropertyOptions(self, propname):
        """
        Returns a list of possible options for a given zProperty
        """
        if propname == "zCollectorPlugins":
            from Products.DataCollector.Plugins import loadPlugins

            return tuple(sorted(p.pluginName for p in loadPlugins(self.dmd)))
        if propname == "zCommandProtocol":
            return ("ssh", "telnet")
        if propname == "zSnmpVer":
            return ("v1", "v2c", "v3")
        if propname == "zSnmpAuthType":
            return ("",) + authentication_protocols
        if propname == "zSnmpPrivType":
            return ("",) + privacy_protocols
        return ()

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "isLocal")

    def isLocal(self, propname):
        """Check to see if a name is local to our current context."""
        v = getattr(aq_base(self), propname, zenmarker)
        return v != zenmarker

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "getOverriddenObjects")

    def getOverriddenObjects(self, propname, showDevices=False):
        """
        Get the objects that override a property somewhere below in the tree.
        """
        if showDevices:
            objects = []
            for inst in self.getSubInstances("devices"):
                if inst.isLocal(propname) and inst not in objects:
                    objects.append(inst)
            for suborg in self.children():
                if suborg.isLocal(propname):
                    objects.append(suborg)
                for inst in suborg.getOverriddenObjects(propname, showDevices):
                    if inst not in objects:
                        objects.append(inst)
            return objects
        return [
            org for org in self.getSubOrganizers() if org.isLocal(propname)
        ]

    def _findParentWithProperty(self, id):
        """Returns self or the first acquisition parent that has a property
        with the id.  Returns None if no parent had the id.
        """
        return next(
            (
                ob
                for ob in aq_chain(self)
                if isinstance(ob, ZenPropertyManager) and ob.hasProperty(id)
            ),
            None,
        )

    def hasProperty(self, id, useAcquisition=False):
        """Override method in PropertyManager to support acquisition."""
        if useAcquisition:
            hasProp = self._findParentWithProperty(id) is not None
        else:
            hasProp = PropertyManager.hasProperty(self, id)
        return hasProp

    def getProperty(self, id, d=None):
        """Get property value and apply transformer.  Overrides method in
        Zope's PropertyManager class.  Acquire values from aquisiton parents
        if needed.
        """
        ob = self._findParentWithProperty(id)
        return d if (ob is None) else PropertyManager.getProperty(ob, id, d)

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "getPropertyType")

    def getPropertyType(self, id):
        """Overrides methods from PropertyManager to support acquisition."""
        ob = self._findParentWithProperty(id)
        if ob is not None:
            return PropertyManager.getPropertyType(ob, id)

    security.declareProtected(ZEN_ZPROPERTIES_VIEW, "getZ")

    def getZ(self, id, default=None):
        """Return the value of a zProperty on this object.  This method is
        used to lookup zProperties for a user with a role that doesn't have
        direct access to an attribute further up the acquisition path.  If the
        requested property is a password, then None is returned.

        @param id: id of zProperty
        @type id: string
        @return: Value of zProperty
        @permission: ZEN_ZPROPERTIES_VIEW

        >>> dmd.Devices.getZ('zSnmpPort')
        161
        >>> dmd.Devices.getZ('zSnmpAuthPassword')
        >>>
        """
        if self.hasProperty(
            id, useAcquisition=True
        ) and not self.zenPropIsPassword(id):
            return self.getProperty(id)
        return default

    def exportZProperties(self, exclusionList=()):
        """
        @param exclusionList: list of zproperties we do not want to export
        @type exclusionList: collection
        For this manager will return the following about each zProperty
        Will return the following about each Zen Property
        - id - identifier
        - islocal - if this object has a local definition
        - value - value for this object
        - valueAsString - string representation of the property
        - type - int string lines etc
        - path - where it is defined
        - options - acceptable values of this zProperty
        """
        props = []
        root = self.getDmdRoot(self.dmdRootName)
        for zId in self.zenPropertyIds():
            if zId in exclusionList:
                continue
            prop = self.exportZProperty(zId, root)
            if not self.zenPropIsPassword(zId):
                prop["value"] = self.getZ(zId)
            else:
                prop["value"] = self.zenPropertyString(zId)

            # look up the description and label from the root
            props.append(prop)

        return props

    def exportZProperty(self, zId, root=None):
        if not root:
            root = self.getDmdRoot(self.dmdRootName)
        return dict(
            id=zId,
            islocal=self.hasProperty(zId),
            type=self.getPropertyType(zId),
            path=self.zenPropertyPath(zId),
            options=self.zenPropertyOptions(zId),
            category=getzPropertyCategory(zId),
            value=None,
            valueAsString=self.zenPropertyString(zId),
            label=root.propertyLabel(zId),
            description=root.propertyDescription(zId),
        )


InitializeClass(ZenPropertyManager)


class IdentityTransformer(object):
    "A do-nothing transformer to use as the default"

    def transformForGet(self, value):
        return value

    def transformForSet(self, value):
        return value


def monkeypatchDescriptors(zprops, transformerFactories):
    """
    monkeypatch ZenPropertyManager adding an instance of the descriptor class
    for each of the zProperties
    """
    for id, type in zprops:
        factory = transformerFactories.get(type, IdentityTransformer)
        descriptor = PropertyDescriptor(id, type, factory())
        setattr(ZenPropertyManager, id, descriptor)


def setDescriptors(dmd):
    """
    Set the property descriptors on the ZenPropertyManager class.  The
    transformerFactories parameter is a dictionary that maps a property type
    to a callable factory that produces instances with transformForGet and
    transformForSet methods.
    """
    zprops = {}

    # copy the core zProps
    # Z_PROPERTIES = id, defaultValue, type , label, description
    for item in Z_PROPERTIES:
        id = item[0]
        type = item[2]
        zprops[id] = (id, type)
        Z_PROPERTY_META_DATA[id] = dict()
        Z_PROPERTY_META_DATA[id]["type"] = type
        Z_PROPERTY_META_DATA[id]["defaultValue"] = item[1]
        if len(item) >= 4:
            Z_PROPERTY_META_DATA[id]["label"] = item[3]
        if len(item) >= 5:
            Z_PROPERTY_META_DATA[id]["description"] = item[4]

    # add zProps from zenpacks
    for zpkg in pkg_resources.iter_entry_points("zenoss.zenpacks"):
        # fromlist is typically ZenPacks.zenoss
        fromlist = zpkg.module_name.split(".")[:-1]
        module = __import__(zpkg.module_name, globals(), locals(), fromlist)
        if hasattr(module, "ZenPack"):
            # Merge ZenPack.packZProperties and ZenPack.packZProperties_data.
            # packZProperties wins if they disagree about type or defaultValue.
            for p_id, p_data in module.ZenPack.getZProperties().items():
                if p_id in zprops:
                    log.warning(
                        "%s tried to override existing %s property.",
                        zpkg.module_name,
                        p_id,
                    )
                    continue

                zprops[p_id] = (p_id, p_data["type"])

                category = p_data.get("category")
                if category:
                    setzPropertyCategory(p_id, category)

                Z_PROPERTY_META_DATA[p_id] = {
                    "type": p_data.get("type", "string"),
                    "defaultValue": p_data.get("defaultValue"),
                    "label": p_data.get("label"),
                    "description": p_data.get("description"),
                    "category": category,
                }

    # add zProps from dmd.Devices to catch any that are undefined elsewhere
    for p_id in dmd.Devices.zenPropertyIds():
        p_type = dmd.Devices.getPropertyType(p_id)
        if p_id not in zprops:
            zprops[p_id] = (p_id, p_type)
            log.debug(
                "Property %s is deprecated. It should be removed "
                "from the system.",
                p_id,
            )

    monkeypatchDescriptors(zprops.values(), dmd.propertyTransformers)


def updateDescriptors(type, transformer):
    """
    Update all descriptors with the specified type to use the specified
    transformer.
    """
    for var in vars(ZenPropertyManager):
        attr = getattr(ZenPropertyManager, var)
        if isinstance(attr, PropertyDescriptor) and attr.type == type:
            attr.transformer = transformer
