##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

MAPPINGS = {
    #
    # Modeler Controls
    # ----------
    "zCollectorClientTimeout": "Modeler Controls",
    "zCollectorDecoding": "Modeler Controls",
    "zCollectorPlugins": "Modeler Controls",
    "zFileSystemMapIgnoreNames": "Modeler Controls",
    "zFileSystemMapIgnoreTypes": "Modeler Controls",
    "zInterfaceMapIgnoreNames": "Modeler Controls",
    "zInterfaceMapIgnoreTypes": "Modeler Controls",
    "zIpServiceMapMaxPort": "Modeler Controls",
    "zLocalInterfaceNames": "Modeler Controls",
    "zLocalIpAddresses": "Modeler Controls",
    "zRouteMapCollectOnlyIndirect": "Modeler Controls",
    "zRouteMapCollectOnlyLocal": "Modeler Controls",
    "zRouteMapMaxRoutes": "Modeler Controls",
    "zHardDiskMapMatch": "Modeler Controls",
    #
    # zencommand
    # ----------
    "zCommandCollectionInterval": "zencommand",
    "zCommandCommandTimeout": "zencommand",
    "zCommandUserCommandTimeout": "zencommand",
    "zCommandExistanceTest": "zencommand",
    "zCommandLoginTimeout": "zencommand",
    "zCommandLoginTries": "zencommand",
    "zCommandPassword": "zencommand",
    "zCommandPath": "zencommand",
    "zCommandPort": "zencommand",
    "zCommandProtocol": "zencommand",
    "zCommandSearchPath": "zencommand",
    "zCommandUsername": "zencommand",
    "zKeyPath": "zencommand",
    #
    # Configuration Cache
    # -------------------
    "zDeviceConfigTTL": "Config Cache",
    "zDeviceConfigMinimumTTL": "Config Cache",
    "zDeviceConfigBuildTimeout": "Config Cache",
    "zDeviceConfigPendingTimeout": "Config Cache",
    #
    # Misc
    # ---------
    "zDeviceTemplates": "Misc",
    "zFileSystemSizeOffset": "Misc",
    "zIcon": "Misc",
    "zIfDescription": "Misc",
    "zLinks": "Misc",
    "zPingMonitorIgnore": "Misc",
    "zProdStateThreshold": "Misc",
    "zPythonClass": "Misc",
    "zStatusConnectTimeout": "Misc",
    "zStatusEventClass": "Misc",
    "zNoRelationshipCopy": "Misc",
    #
    # SNMP
    # ----------
    "zMaxOIDPerRequest": "SNMP",
    "zSnmpEngineId": "SNMP",
    "zSnmpAuthPassword": "SNMP",
    "zSnmpAuthType": "SNMP",
    "zSnmpCollectionInterval": "SNMP",
    "zSnmpCommunities": "SNMP",
    "zSnmpCommunity": "SNMP",
    "zSnmpMonitorIgnore": "SNMP",
    "zSnmpPort": "SNMP",
    "zSnmpPrivPassword": "SNMP",
    "zSnmpPrivType": "SNMP",
    "zSnmpSecurityName": "SNMP",
    "zSnmpTimeout": "SNMP",
    "zSnmpTries": "SNMP",
    "zSnmpVer": "SNMP",
    "zSnmpContext": "SNMP",
    #
    # ZenPacks
    # ========
    # CiscoMonitor
    # ----------
    "zIdiomPassword": "CiscoMonitor",
    "zIdiomUsername": "CiscoMonitor",
    #
    # RANCID
    # ----------
    "zRancidGroup": "RANCID",
    "zRancidRoot": "RANCID",
    "zRancidType": "RANCID",
    "zRancidUrl": "RANCID",
    #
    # CiscoUCS
    # ----------
    "zCiscoUCSManagerPassword": "CiscoUCS",
    "zCiscoUCSManagerPort": "CiscoUCS",
    "zCiscoUCSManagerUser": "CiscoUCS",
    "zCiscoUCSManagerUseSSL": "CiscoUCS",
    #
    # Sugar
    # ----------
    "zSugarCRMBase": "Sugar",
    "zSugarCRMPassword": "Sugar",
    "zSugarCRMTestAccount": "Sugar",
    "zSugarCRMUsername": "Sugar",
    #
    # Dell
    # ----------
    "zSysedgeDiskMapIgnoreNames": "Dell",
    #
    # Telnet
    # ----------
    "zTelnetEnable": "Telnet",
    "zTelnetEnableRegex": "Telnet",
    "zTelnetLoginRegex": "Telnet",
    "zTelnetPasswordRegex": "Telnet",
    "zTelnetPromptTimeout": "Telnet",
    "zTelnetSuccessRegexList": "Telnet",
    "zTelnetTermLength": "Telnet",
    #
    # vCloud
    # ----------
    "zVCloudPassword": "vCloud",
    "zVCloudPort": "vCloud",
    "zVCloudUsername": "vCloud",
    #
    # VMware
    # ----------
    "zVMwareViEndpointHost": "VMware",
    "zVMwareViEndpointMonitor": "VMware",
    "zVMwareViEndpointPassword": "VMware",
    "zVMwareViEndpointUser": "VMware",
    "zVMwareViEndpointUseSsl": "VMware",
    #
    # WebSphere
    # ----------
    "zWebsphereAuthRealm": "WebSphere",
    "zWebsphereNode": "WebSphere",
    "zWebspherePassword": "WebSphere",
    "zWebsphereServer": "WebSphere",
    "zWebsphereURLPath": "WebSphere",
    "zWebsphereUser": "WebSphere",
}


def setzPropertyCategory(prop, category):
    """
    This is for display purposes only. Set the category of a zproperty.
    This list is not persisted at all so it will need to be called
    each time that zope starts up.
    @type  prop: String
    @param prop: zProperty Id
    @type  category: String
    @param category: What will show as the category for the zproperty
    """
    MAPPINGS[prop] = category


def getzPropertyCategory(prop):
    """
    Uses the mapping defined in this file to
    come up with a category for a given zproperty.
    If none is found "Misc" is returned.
    Note that the category IS case sensitive.
    """
    if MAPPINGS.get(prop):
        return MAPPINGS[prop]
    # if not in this list assume they came from a zenpack
    return "Misc"
