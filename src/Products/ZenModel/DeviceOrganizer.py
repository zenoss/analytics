##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""DeviceOrganizer
Base class for device organizers
"""

from itertools import ifilter
from zope.event import notify
from zope.interface import implements
from ZODB.transact import transact
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from Organizer import Organizer
from DeviceManagerBase import DeviceManagerBase
from Commandable import Commandable
from ZenMenuable import ZenMenuable
from MaintenanceWindowable import MaintenanceWindowable
from AdministrativeRoleable import AdministrativeRoleable
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenWidgets.interfaces import IMessageSender

from ZenossSecurity import ZEN_VIEW, ZEN_MANAGE_DMD, ZEN_COMMON, ZEN_CHANGE_DEVICE_PRODSTATE
from Products.ZenUtils.Utils import unused, getObjectsFromModelCatalog
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenWidgets import messaging
from Products.Jobber.jobs import DeviceSetLocalRolesJob

import logging
LOG = logging.getLogger('ZenModel.DeviceOrganizer')

class DeviceOrganizer(Organizer, DeviceManagerBase, Commandable, ZenMenuable,
                        MaintenanceWindowable, AdministrativeRoleable):
    """
    DeviceOrganizer is the base class for device organizers.
    It has lots of methods for rolling up device statistics and information.
    """
    implements(IGloballyIdentifiable)

    security = ClassSecurityInfo()

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : (ZEN_MANAGE_DMD,)
                },
            )
         },
        )

    _relations =  Organizer._relations + (
        ("maintenanceWindows", ToManyCont(
            ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(
            ToOne,"Products.ZenModel.AdministrativeRole","managedObject")),
        ('userCommands', ToManyCont(
            ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        ('zenMenus', ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenu', 'menuable')),
       )

    def _getSubdevices(self, brains=False):
        """ Helper method to search for devices/devices brains under the current organizer """
        catalog = IModelCatalogTool(self.dmd.Devices)
        query = {}
        query["objectImplements"] = "Products.ZenModel.Device.Device"
        query["path"] = "{0}*".format("/".join(self.getPhysicalPath()))
        if not brains:
            return getObjectsFromModelCatalog(catalog, query, LOG)
        else:
            return catalog.search(query=query).results

    security.declareProtected(ZEN_COMMON, "getSubDevices")
    def getSubDevices(self, devfilter=None):
        """
        Get all the devices under an instance of a DeviceOrganizer

        @param devfilter: Filter function applied to returned list
        @type devfilter: function
        @return: Devices
        @rtype: list

        """
        devices = ifilter(lambda dev:self.checkRemotePerm(ZEN_VIEW, dev), self._getSubdevices())
        devices = ifilter(devfilter, devices)
        return list(devices)

    security.declareProtected(ZEN_VIEW, "getSubDevicesGen")
    def getSubDevicesGen(self, devfilter=None):
        """ get all the devices under and instance of a DeviceGroup """
        devices = ifilter(lambda dev:self.checkRemotePerm(ZEN_VIEW, dev), self._getSubdevices())
        if devfilter:
            devices = ifilter(devfilter, devices)
        for device in devices:
            yield device

    security.declareProtected(ZEN_COMMON, "getSubDevices_recursive")
    def getSubDevices_recursive(self, devfilter=None, devrel="devices"):
        devrelobj = getattr(self, devrel, None)
        if not devrelobj:
            raise AttributeError( "%s not found on %s" % (devrel, self.id) )
        devices = filter(devfilter, devrelobj())
        devices = [ dev for dev in devices
                    if self.checkRemotePerm(ZEN_VIEW, dev)]
        for subgroup in self.children(checkPerm=False):
            devices.extend(subgroup.getSubDevices_recursive(devfilter, devrel))
        return devices

    security.declareProtected(ZEN_VIEW, "getSubDevicesGen")
    def getSubDevicesGen_recursive(self, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devrelobj = getattr(self, devrel, None)
        if not devrelobj:
            raise AttributeError( "%s not found on %s" % (devrel, self.id) )
        for dev in devrelobj.objectValuesGen():
            yield dev
        for subgroup in self.children():
            for dev in subgroup.getSubDevicesGen_recursive(devrel):
                yield dev

    def getSubDevicesGenTest(self, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices:
            raise AttributeError( "%s not found on %s" % (devrel, self.id) )


    def getMonitoredComponents(self):
        """Return monitored components for devices within this DeviceOrganizer.
        """
        cmps = []
        for dev in self.getSubDevicesGen():
            cmps.extend(dev.getMonitoredComponents())
        return cmps


    def getAllCounts(self, devrel="devices"):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        devices = getattr(self, devrel)
        pingStatus = 0
        snmpStatus = 0
        devCount = devices.countObjects()
        for dev in devices():
            if dev.getPingStatusNumber() > 0:
                pingStatus += 1
            if dev.getSnmpStatusNumber() > 0:
                snmpStatus += 1
        counts = [devCount, pingStatus, snmpStatus]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def countDevices(self, devrel="devices"):
        """count all devices with in a device group"""
        unused(devrel)
        count = self.devices.countObjects()
        for group in self.children():
            count += group.countDevices()
        return count


    def pingStatus(self, devrel="devices"):
        """aggrigate ping status for all devices in this group and below"""
        status = self._status("Ping", devrel)
        for group in self.children():
            status += group.pingStatus()
        return status


    def snmpStatus(self, devrel="devices"):
        """aggrigate snmp status for all devices in this group and below"""
        status = self._status("Snmp", devrel)
        for group in self.children():
            status += group.snmpStatus()
        return status


    def _buildDeviceList(self, deviceNames):
        """Build a device list for set methods"""
        if isinstance(deviceNames, basestring):
            deviceNames = [deviceNames]
        if deviceNames is not None:
            deviceNames = set(deviceNames)
        return [d.primaryAq() for d in self.getSubDevices()
                if deviceNames is None or d.id in deviceNames
                or d.getPrimaryId() in deviceNames]


    def deviceClassMoveTargets(self):
        """Return list of all organizers excluding our self."""
        targets = filter(lambda x: x != self.getOrganizerName(),
                            self.dmd.Devices.getOrganizerNames())
        return sorted(targets, key=lambda x: x.lower())


    def moveDevicesToClass(self, moveTarget, deviceNames=None, REQUEST=None):
        """Move Devices from one DeviceClass to Another"""
        if deviceNames is None:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No devices were selected',
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)
        deviceNames = [ x.split('/')[-1] for x in deviceNames ]
        return self.dmd.Devices.moveDevices(moveTarget, deviceNames, REQUEST)


    def _handleOrganizerCall(self, arg=None, deviceNames=None, \
                                isOrganizer=False, REQUEST=None, \
                                deviceMethod=None):
        """ Handle the many many methods that simply call one
        method on device differently"""
        #check to see if we have the essentials to work with
        if not deviceMethod: return
        if deviceNames is None and not isOrganizer:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No devices were selected',
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            devMethod = getattr(dev, deviceMethod, None)
            if devMethod and arg:
                devMethod(arg)
            elif devMethod:
                devMethod()


    def _buildReturnMessage(self, title, message, paths=None, \
                               checkPaths=False):
        """build the standard return message for the various set
        methods"""
        if checkPaths:
            if paths:
                if not isinstance(paths, basestring):
                    paths = ", ".join(paths)
                message += paths
            else:
                message = "%s unset" % message.split(" ")[0]
        if self.REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
            return message
        else:
            IMessageSender(self).sendToBrowser(title, message)
            return self.callZenScreen(self.REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE_PRODSTATE, 'setProdState')
    def setProdState(self, state, deviceNames=None,
                        isOrganizer=False, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        self._handleOrganizerCall(state, deviceNames, isOrganizer, \
                                    REQUEST, "setProdState")
        if REQUEST:
            statename = self.convertProdState(state)
            msg = "Production state set to %s for %s." % (statename,
                                                          " ".join(deviceNames))
            return self._buildReturnMessage("Production State Changed", msg)


    def setPriority(self, priority, deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """Set prioirty of all devices in this Organizer.
        """
        self._handleOrganizerCall(priority, deviceNames, isOrganizer, \
                                    REQUEST, "setPriority")
        if REQUEST:
            priname = self.convertPriority(priority)
            msg = "Priority set to %s for %s." % (priname,
                                                  " ".join(deviceNames))
            return self._buildReturnMessage('Priority Changed', msg)


    def setPerformanceMonitor(self, performanceMonitor=None, deviceNames=None,
                                isOrganizer=False, REQUEST=None):
        """ Provide a method to set performance monitor from any organizer """
        if not performanceMonitor:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No monitor was selected',
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)
        self._handleOrganizerCall(performanceMonitor, deviceNames, isOrganizer, \
                                    REQUEST, "setPerformanceMonitor")
        if REQUEST:
            msg = "Collector set to %s" % (performanceMonitor)
            return self._buildReturnMessage('Collector Set', msg)


    def setGroups(self, groupPaths=None, deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device groups from any organizer """
        if not groupPaths: groupPaths = []
        self._handleOrganizerCall(groupPaths, deviceNames, isOrganizer, \
                                    REQUEST, "setGroups")
        if REQUEST:
            msg = "Groups set to"
            return self._buildReturnMessage('Groups Set', msg, groupPaths, True)


    def setSystems(self, systemPaths=None, deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device systems from any organizer """
        if not systemPaths: systemPaths = []
        self._handleOrganizerCall(systemPaths, deviceNames, isOrganizer, \
                                    REQUEST, "setSystems")
        if REQUEST:
            msg = "Systems set to"
            return self._buildReturnMessage('Systems Set', msg, systemPaths, True)

    def setLocation(self, locationPath="", deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device location from any organizer """
        self._handleOrganizerCall(locationPath, deviceNames, isOrganizer, \
                                    REQUEST, "setLocation")
        if REQUEST:
            msg = "Location set to %s" % locationPath
            return self._buildReturnMessage('Location Set', msg)

    def unlockDevices(self, deviceNames=None, isOrganizer=False, REQUEST=None):
        """Unlock devices"""
        self._handleOrganizerCall(None, deviceNames, isOrganizer, \
                                    REQUEST, "unlock")
        if REQUEST:
            msg = "Devices unlocked"
            return self._buildReturnMessage('Devices Unlocked', msg)

    def lockDevicesFromDeletion(self, deviceNames=None,
                    sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted"""
        self._handleOrganizerCall(sendEventWhenBlocked, deviceNames, isOrganizer, \
                                    REQUEST, "lockFromDeletion")
        if REQUEST:
            msg = "Devices locked from deletion"
            return self._buildReturnMessage('Devices Locked', msg)

    def lockDevicesFromUpdates(self, deviceNames=None,
                sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted or updated"""
        self._handleOrganizerCall(sendEventWhenBlocked, deviceNames, isOrganizer, \
                                    REQUEST, "lockFromUpdates")
        if REQUEST:
            msg = "Devices locked from updates and deletion"
            return self._buildReturnMessage('Devices Locked', msg)


    def index_object(self, idxs=None):
        """No action.
        Index of subdevices will happen in manage_addAdministrativeRole
        """
        pass

    def unindex_object(self):
        """No action.
        Unindex of subdevices will happen in manage_deleteAdministrativeRole
        """
        pass

    def _setDeviceLocalRoles(self):
        def deviceChunk(devices, chunksize=10):
            i = 0
            maxi = len(devices)
            while i < maxi:
                nexti = i+chunksize
                yield devices[i:nexti]
                i = nexti

        @transact
        def setLocalRoles(devices):
            for device in devices:
                device = device.primaryAq()
                device.setAdminLocalRoles()

        devices = self.getSubDevices()
        total = len(devices)
        count = 0
        for chunk in deviceChunk(devices):
            count += len(chunk)
            LOG.info("Setting admin roles on %d of total %d", count, total)
            setLocalRoles(chunk)

    def _maybeCreateLocalRolesJob(self):
        """
        Look at our total number of devices if it is above the threshold
        then submit a job for updating the admin roles.
        """
        path = "/".join(self.getPhysicalPath())
        threshold = getattr(self.dmd.UserInterfaceSettings, "deviceMoveJobThreshold", 5)

        # find out how many devices we have by just looking at the brains
        brains = list(self._getSubdevices(brains=True))

        if len(brains) > threshold:
            job = self.dmd.JobManager.addJob(
                DeviceSetLocalRolesJob, description="Update Local Roles on %s" % path,
                kwargs=dict(organizerUid=path))
            href = "/zport/dmd/joblist#jobs:%s" % (job.jobid,)
            messaging.IMessageSender(self).sendToBrowser(
                'Job Added',
                'Job Added for setting the roles on the organizer %s, view the <a href="%s"> job log</a>' % (path, href)
            )
            return job
        return self._setDeviceLocalRoles()

    def manage_addAdministrativeRole(self, newId, REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_addAdministrativeRole
        Adds an administrator to this DeviceOrganizer

        @param userid: User to make an administrator of this Organizer
        @type userid: string
        """

        AdministrativeRoleable.manage_addAdministrativeRole(self, newId)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._maybeCreateLocalRolesJob()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                'Administrative role %s was added.' % newId
            )
            return self.callZenScreen(REQUEST)


    def manage_editAdministrativeRoles(self, ids=(), role=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_editAdministrativeRoles
        Edit the administrators to this DeviceOrganizer
        """
        AdministrativeRoleable.manage_editAdministrativeRoles(
                                         self,ids,role)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._maybeCreateLocalRolesJob()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                'Administrative roles were updated: %s' % ', '.join(ids)
            )
            return self.callZenScreen(REQUEST)


    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_deleteAdministrativeRole
        Deletes administrators to this DeviceOrganizer

        @param delids: Users to delete from this Organizer
        @type delids: tuple of strings
        """
        AdministrativeRoleable.manage_deleteAdministrativeRole(self, delids)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._maybeCreateLocalRolesJob()
        if REQUEST:
            if delids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Deleted',
                    'Administrative roles were deleted: %s' % ', '.join(delids)
                )
            return self.callZenScreen(REQUEST)


    def manage_snmpCommunity(self, REQUEST=None):
        """reset Community on all devices in this Organizer.
        """
        [ d.manage_snmpCommunity() for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def setManageIp(self, REQUEST=None):
        """reset ip on all devices in this Organizer.
        """
        [ d.setManageIp() for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def collectDevice(self, REQUEST=None, write=None, debug=False):
        """model all devices in this Organizer.
        """
        subDevices = list(self.getSubDevices())
        if not subDevices and write:
            write("No devices found in organizer.")
        for d in subDevices:
            d.collectDevice(REQUEST=REQUEST, write=write, debug=debug)
        if (not write and REQUEST):
            return self.callZenScreen(REQUEST)

    def runDeviceMonitor(self, REQUEST=None, write=None, debug=False):
        """run monitoring for all devices in this Organizer.
        """
        subDevices = list(self.getSubDevices())
        if not subDevices and write:
            write("No devices found in organizer.")
        for d in subDevices:
            d.runDeviceMonitor(REQUEST=REQUEST, write=write, debug=debug)
        if (not write and REQUEST):
            return self.callZenScreen(REQUEST)

    def _status(self, type, devrel="devices"):
        """build status info for device in this device group"""
        status = 0
        statatt = "get%sStatusNumber" % type
        devices = getattr(self, devrel, None)
        if not devices:
            raise AttributeError( "%s not found on %s" % (devrel, self.id) )
        for device in devices():
            if getattr(device, statatt, -1)() > 0:
                status += 1
        return status

    def statusColor(self, status):
        """colors for status fields for device groups"""
        retval = '#00ff00'
        if status == -1:
            retval = "#d02090"
        elif status == 1:
            retval = '#ffff00'
        elif status == 2:
            retval = '#ff9900'
        elif status > 2:
            retval = '#ff0000'
        return retval

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.getSubDevices()

    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/deviceOrganizerManage'

    def getLinks(self, recursive=True):
        """ Return all Links on all interfaces on all
            Devices in this Organizer
        """
        alllinks = []
        if recursive:
            devices = self.getSubDevicesGen()
        else:
            devices = self.devices.objectValuesGen()
        for device in devices:
            alllinks.extend(list(device.getLinks()))
        return alllinks

    security.declareProtected(ZEN_VIEW, 'getIconPath')
    def getIconPath(self):
        """ Override the zProperty icon path and return a folder
        """
        return "/zport/dmd/img/icons/folder.png"

    security.declareProtected(ZEN_VIEW, 'getPrettyLink')
    def getPrettyLink(self, noicon=False, shortDesc=False):
        """ Gets a link to this object, plus an icon """
        href = self.getPrimaryUrlPath().replace('%','%%')
        linktemplate = "<a href='"+href+"' class='prettylink'>%s</a>"
        icon = ("<div class='device-icon-container'> "
                "<img class='device-icon' src='%s'/> "
                "</div>") % self.getIconPath()
        name = self.getPrimaryDmdId()
        if noicon: icon=''
        if shortDesc: name = self.id
        rendered = icon + name
        if not self.checkRemotePerm("View", self):
            return rendered
        else:
            return linktemplate % rendered

InitializeClass(DeviceOrganizer)
