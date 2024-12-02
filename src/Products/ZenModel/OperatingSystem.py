##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.OS")

from Software import Software

from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from Products.ZenModel.Exceptions import *
from Products.ZenModel.Service import Service

from IpInterface import manage_addIpInterface
from WinService import manage_addWinService
from IpService import manage_addIpService
from OSProcess import manage_addOSProcess, OSProcess
from IpRouteEntry import manage_addIpRouteEntry
from FileSystem import manage_addFileSystem

from Products.ZenWidgets import messaging
from Products.ZenUtils.Utils import prepId

class OperatingSystem(Software):

    totalSwap = 0
    uname = ""

    _properties = Software._properties + (
        {'id':'totalSwap', 'type':'long', 'mode':'w'},
        {'id':'uname', 'type':'string', 'mode':''},
    )

    _relations = Software._relations + (
        ("interfaces", ToManyCont(ToOne,
            "Products.ZenModel.IpInterface", "os")),
        ("routes", ToManyCont(ToOne, "Products.ZenModel.IpRouteEntry", "os")),
        ("ipservices", ToManyCont(ToOne, "Products.ZenModel.IpService", "os")),
        ("winservices", ToManyCont(ToOne,
            "Products.ZenModel.WinService", "os")),
        ("processes", ToManyCont(ToOne, "Products.ZenModel.OSProcess", "os")),
        ("filesystems", ToManyCont(ToOne,
            "Products.ZenModel.FileSystem", "os")),
        ("software", ToManyCont(ToOne, "Products.ZenModel.Software", "os")),
    )

    security = ClassSecurityInfo()

    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')

    factory_type_information = (
        {
            'id'             : 'Device',
            'meta_type'      : 'Device',
            'description'    : """Base class for all devices""",
            'icon'           : 'Device_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDevice',
            'immediate_view' : '../deviceOsDetail',
            'actions'        : ()
         },
        )


    def __init__(self):
        id = "os"
        Software.__init__(self, id)
        self._delObject("os")   # OperatingSystem is a software 
                                # but doens't have os relationship


    def totalSwapString(self):
        return self.totalSwap and convToUnits(self.totalSwap) or 'Unknown'

    def traceRoute(self, target, ippath):
        """
        Trace the route to the target from this device using our routing 
        table and return an array of IP address strings showing the route.

        If the route is not traversable (ie a gap in the routing table),
        then return the incomplete path with a final value of None.

        @parameter target: destination IP to find
        @type target: DMD device object
        @parameter ippath: used to store intermediate results in calls. Call with []
        @type ippath: array-like object used for 
        @return: IP addresses to target device
        @rtype: array of strings
        """
        log.debug("traceRoute from device %s to target %s",
                  self.getDeviceName(), target)
        # Try to find a specific route to the target device
        nextdev = None
        for route in sorted(self.getRouteObjs(),key=lambda route:route.routemask,reverse=True):
            ip = route.getNextHopIp()
            log.debug("Route %s next hop %s", route.getTarget(), ip)
            # Have a host-route
            if ip == target.getManageIp():
                ippath.append(ip)
                return ippath

            # Have a net-route
            if route.matchTarget(target.getManageIp()):
                if route.routetype == 'direct':
                    nextdev = target
                    break
                nextdev = route.getNextHopDevice()
                break
        else:
            # No routes matched -- try the default route (if any)
            log.debug("Device %s default route", self.getDeviceName())
            ip = ""
            default = self.routes._getOb("0.0.0.0_0", None)
            if default:
                ip = default.getNextHopIp()
                nextdev = default.getNextHopDevice()

        if target == nextdev or ip == "0.0.0.0":
            ippath.append(target.id)
            return ippath

        if nextdev:
            # Look for a bizarre case where we find a loop
            if nextdev.manageIp not in ippath:
                ippath.append(ip)
                return nextdev.traceRoute(target, ippath)

        # Oops!  No route!
        log.debug("Unable to trace to %s, gap at %s", target.id,
                            self.getDeviceName())
        ippath.append(None)
        return ippath


    def getRouteObjs(self):
        """Return our real route objects.
        """
        return filter(lambda r: r.target(), self.routes())


    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()

    def deleteDeviceComponents(self, context, componentNames=[], REQUEST=None):
        """Delete device components"""
        if not componentNames: return self()
        if isinstance(componentNames, basestring):
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName, False)
            if dc: dc.manage_deleteComponent()
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def unlockDeviceComponents(self, context, componentNames=[], REQUEST=None):
        """Unlock device components"""
        if not componentNames: return self()
        if isinstance(componentNames, basestring):
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.unlock()
        if REQUEST:
            return self.callZenScreen(REQUEST)
            
    def lockDeviceComponentsFromDeletion(self, context, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from deletion"""
        if not componentNames: return self()
        if isinstance(componentNames, basestring):
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.lockFromDeletion(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def lockDeviceComponentsFromUpdates(self, context, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from updates"""
        if not componentNames: return self()
        if isinstance(componentNames, basestring):
            componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName, False)
            if dc: dc.lockFromUpdates(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def addIpInterface(self, newId, userCreated, REQUEST=None):
        """Add IpInterfaces.
        """
        manage_addIpInterface(self.interfaces, newId, userCreated)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Interface Created',
                'IP Interface %s was created.' % newId
            )
            REQUEST['RESPONSE'].redirect(
                self.interfaces._getOb(newId).absolute_url_path())
            self._p_changed = True
            return self.callZenScreen(REQUEST)

    def deleteIpInterfaces(self, componentNames=[], REQUEST=None):
        """Delete IpInterfaces"""
        self.deleteDeviceComponents(self.interfaces, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Interfaces Deleted',
                'IP Interfaces %s was created.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def setComponentMonitored(self, context, componentNames=[],
                               monitored=True, REQUEST=None):
        """
        Set monitored status for selected components.
        """
        if isinstance(context, basestring):
            context = getattr(self, context)
        if not componentNames: return self()
        if isinstance(componentNames, basestring):
            componentNames = (componentNames,)
        monitored = bool(monitored)
        for componentName in componentNames:
            comp = context._getOb(componentName, False)
            if comp and comp.monitored() != monitored:
                comp.monitor = monitored
                if isinstance(comp, (Service, OSProcess)):
                    comp.setAqProperty('zMonitor', monitored, 'boolean')
                comp.index_object()
        if REQUEST:
            verb = monitored and "Enabled" or "Disabled"
            messaging.IMessageSender(self).sendToBrowser(
                'Monitoring %s' % verb,
                'Monitoring was %s on %s.' % (verb.lower(),
                                              ', '.join(componentNames))
            )
            return self.callZenScreen(REQUEST)

    def unlockIpInterfaces(self, componentNames=[], REQUEST=None):
        """Unlock IpInterfaces"""
        self.unlockDeviceComponents(self.interfaces, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Interfaces Unlocked',
                'Interfaces %s were unlocked.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)
        
    def lockIpInterfacesFromDeletion(self, componentNames=[],
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from deletion"""
        self.lockDeviceComponentsFromDeletion(self.interfaces, componentNames,
            sendEventWhenBlocked, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Interfaces Locked',
                'Interfaces %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)
        
    def lockIpInterfacesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from updates"""
        self.lockDeviceComponentsFromUpdates(self.interfaces, componentNames,
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Interfaces Locked',
                'Interfaces %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def addWinService(self, newClassName, userCreated, REQUEST=None):
        """Add an WinService.
        """
        org = self.dmd.Services
        wsc = org.unrestrictedTraverse(newClassName)
        if wsc is not None:
            ws = manage_addWinService(self.winservices, 
                                    wsc.id,
                                    wsc.description,
                                    userCreated=userCreated,
                                    newClassName=newClassName)
            self._p_changed = True
        elif REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'No Such WinService',
                'Could not find a WinService named %s.' % (newClassName),
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'WinService Added',
                'WinService %s was added.' % (newClassName)
            )
            REQUEST['RESPONSE'].redirect(ws.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def deleteWinServices(self, componentNames=[], REQUEST=None):
        """Delete WinServices"""
        self.deleteDeviceComponents(self.winservices, componentNames, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'WinServices Deleted',
                'WinServices %s were deleted.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def unlockWinServices(self, componentNames=[], REQUEST=None):
        """Unlock WinServices"""
        self.unlockDeviceComponents(self.winservices, componentNames, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'WinServices Unlocked',
                'WinServices %s were unlocked.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)
        
    def lockWinServicesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from deletion"""
        self.lockDeviceComponentsFromDeletion(self.winservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'WinServices Locked',
                'WinServices %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)
        
    def lockWinServicesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from updates"""
        self.lockDeviceComponentsFromUpdates(self.winservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'WinServices Locked',
                'WinServices %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)
    
    def getSubOSProcessClassesGen(self, REQUEST=None):
        """Get OS Process
        """
        return self.getDmdRoot('Processes').getSubOSProcessClassesGen()
        
    def addOSProcess(self, newClassName, example, userCreated, REQUEST=None):
        """Add an OSProcess.
        """
        osp = manage_addOSProcess(self.processes, newClassName, example, userCreated)
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Process Created',
                'OS process %s was created.' % newClassName
            )
            REQUEST['RESPONSE'].redirect(osp.absolute_url_path())

    def deleteOSProcesses(self, componentNames=[], REQUEST=None):
        """Delete OSProcesses"""
        self.deleteDeviceComponents(self.processes, componentNames, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Processes Deleted',
                'OS processes %s were deleted.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def unlockOSProcesses(self, componentNames=[], REQUEST=None):
        """Unlock OSProcesses"""
        self.unlockDeviceComponents(self.processes, componentNames, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Processes Unlocked',
                'OS Processes %s were unlocked.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockOSProcessesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from deletion"""
        self.lockDeviceComponentsFromDeletion(self.processes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Processes Locked',
                'OS processes %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockOSProcessesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from updates"""
        self.lockDeviceComponentsFromUpdates(self.processes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Processes Locked',
                'OS processes %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def addIpService(self, newClassName, protocol, userCreated, REQUEST=None):
        """Add IpServices.
        """
        org = self.dmd.Services
        ipsc = org.unrestrictedTraverse(newClassName)
        if ipsc is not None:
            ips = manage_addIpService(self.ipservices,
                                ipsc.id,
                                protocol,
                                ipsc.port, 
                                userCreated=userCreated)
            self._p_changed = True
        elif REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'No Such WinService',
                'Could not find an IP Service named %s.' % (newClassName),
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'IP Service Added',
                'IP Service %s was added.' % (newClassName)
            )
            REQUEST['RESPONSE'].redirect(ips.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def deleteIpServices(self, componentNames=[], REQUEST=None):
        """Delete IpServices"""
        self.deleteDeviceComponents(self.ipservices, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'IP Services Deleted',
                'IP Services %s were deleted.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def unlockIpServices(self, componentNames=[], REQUEST=None):
        """Unlock IpServices"""
        self.unlockDeviceComponents(self.ipservices, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'IpServices Unlocked',
                'IP Services %s were unlocked.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockIpServicesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from deletion"""
        self.lockDeviceComponentsFromDeletion(self.ipservices, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Services Locked',
                'IP services %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockIpServicesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from updates"""
        self.lockDeviceComponentsFromUpdates(self.ipservices, componentNames,
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Services Locked',
                'IP services %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def addFileSystem(self, newId, userCreated, REQUEST=None):
        """Add a FileSystem.
        """
        fsid = prepId(newId)
        manage_addFileSystem(self.filesystems, newId, userCreated)
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystem Added',
                'Filesystem %s was added.' % newId
            )
            REQUEST['RESPONSE'].redirect(
                self.filesystems._getOb(fsid).absolute_url_path())
            return self.callZenScreen(REQUEST)

    def deleteFileSystems(self, componentNames=[], REQUEST=None):
        """Delete FileSystems"""
        self.deleteDeviceComponents(self.filesystems, componentNames, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystems Deleted',
                'Filesystems %s were deleted.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def unlockFileSystems(self, componentNames=[], REQUEST=None):
        """Unlock FileSystems"""
        self.unlockDeviceComponents(self.filesystems, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystems Unlocked',
                'Filesystems %s were unlocked.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockFileSystemsFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from deletion"""
        self.lockDeviceComponentsFromDeletion(self.filesystems, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystems Locked',
                'Filesystems %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockFileSystemsFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from updates"""
        self.lockDeviceComponentsFromUpdates(self.filesystems, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystems Locked',
                'Filesystems %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def addIpRouteEntry(self, dest, routemask, nexthopid, interface, 
                        routeproto, routetype, userCreated, REQUEST=None):
        """Add an IpRouteEntry.
        """
        manage_addIpRouteEntry(self.routes,
                                dest,
                                routemask,
                                nexthopid,
                                interface,
                                routeproto,
                                routetype,
                                userCreated=userCreated)
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Route Created',
                'IP route entry was created.'
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def deleteIpRouteEntries(self, componentNames=[], REQUEST=None):
        """Delete IpRouteEntries"""
        self.deleteDeviceComponents(self.routes, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Routes Deleted',
                'IP route entries %s were deleted.' % (', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def unlockIpRouteEntries(self, componentNames=[], REQUEST=None):
        """Unlock IpRouteEntries"""
        self.unlockDeviceComponents(self.routes, componentNames, REQUEST)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Routes Unlocked',
                'IP route entries %s were unlocked.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockIpRouteEntriesFromDeletion(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from deletion"""
        self.lockDeviceComponentsFromDeletion(self.routes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Routes Locked',
                'IP route entries %s were locked from deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

    def lockIpRouteEntriesFromUpdates(self, componentNames=[], 
            sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from updates"""
        self.lockDeviceComponentsFromUpdates(self.routes, componentNames, 
            sendEventWhenBlocked, REQUEST)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Routes Locked',
                'IP route entries %s were locked from updates and deletion.' % (
                    ', '.join(componentNames))
            )
            REQUEST['RESPONSE'].redirect(self.absolute_url_path())
            return self.callZenScreen(REQUEST)

InitializeClass(OperatingSystem)
