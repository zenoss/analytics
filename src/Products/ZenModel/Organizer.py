##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """Organizer
Base class for all Zenoss organizers
"""

from AccessControl.class_init import InitializeClass
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo, getSecurityManager

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenWidgets import messaging
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.Utils import getDisplayType, getDisplayName, unpublished

from EventView import EventView
from ZenModelRM import ZenModelRM
from ZenossSecurity import *

class Organizer(ZenModelRM, EventView):
    """
    The base for all hierarchical organization classes.  It allows Organizers
    to be addressed and created with file system like paths like
    /Devices/Servers.  Organizers have a containment relation called children.
    Subclasses must define the attribute:

    dmdRootName - root in the dmd database for this organizer
    """

    _properties = (
                    {'id':'description', 'type':'string', 'mode':'w'},
                   )

    _relations = ZenModelRM._relations

    security = ClassSecurityInfo()
    security.declareObjectProtected(ZEN_VIEW)

    def __init__(self, id, description = ''):
        """
        @param id: Name of this organizer
        @type id: string
        @param description: A decription of this organizer
        @type description: string
        @rtype: Organizer
        """
        ZenModelRM.__init__(self, id)
        self.description = description

    @unpublished
    def urlLink(self, text=None, url=None, attrs={}):
        """
        Override urlLink to return a link with the full path of the organizer.

        >>> dmd.Devices.Server.urlLink()
        '<a href="/zport/dmd/Devices/Server">/Server</a>'
        """
        if text is None: text = self.getOrganizerName()
        return ZenModelRM.urlLink(self, text=text, url=url, attrs=attrs)


    def childMoveTargets(self):
        """
        Returns a list of all organizer names
        under the same root excluding ourselves

        @return: A list of organizers excluding our self.
        @rtype: list
        @todo: We should be using either deviceMoveTargets or childMoveTargets

        >>> dmd.Events.getOrganizerName() in dmd.Events.childMoveTargets()
        False
        """
        myname = self.getOrganizerName()
        return filter(lambda x: x != myname,
                    self.getDmdRoot(self.dmdRootName).getOrganizerNames())

    def getChildMoveTarget(self, moveTargetName):
        """
        Returns an organizer under the same root.

        @param moveTargetName: Name of the organizer
        @type moveTargetName: string
        @rtype: Organizer

        >>> dmd.Devices.getChildMoveTarget('Server')
        <DeviceClass at /zport/dmd/Devices/Server>
        """
        return self.getDmdRoot(self.dmdRootName).getOrganizer(moveTargetName)


    security.declareProtected(ZEN_COMMON, "children")
    def children(self, sort=False, checkPerm=True, spec=None):
        """
        Returns the immediate children of an organizer

        @param sort: If True, sorts the returned children.
        @type sort: boolean
        @param checkPerm: If True, checks if the user has the permission
            to view each child.
        @type checkPerm: boolean
        @param spec: If set, returns children of the specified meta_type.
        @type spec: string
        @return: A list of children of the organizer
        @rtype: list
        @permission: ZEN_COMMON

        >>> dmd.Devices.Printer.children()
        [<DeviceClass at /zport/dmd/Devices/Printer/Laser>,
        <DeviceClass at /zport/dmd/Devices/Printer/InkJet>]
        """
        if spec is None:
            spec = self.meta_type
        kids = self.objectValues(spec=spec)
        if checkPerm:
            kids = [ kid for kid in kids if self.checkRemotePerm(ZEN_VIEW, kid)]
        if sort:
            kids.sort(key=lambda x: x.primarySortKey())
        return kids


    def childIds(self, spec=None):
        """
        Returns the ids of the immediate children of an organizer

        @param spec: If set, returns children of the specified meta_type.
        @type spec: string
        @return: Ids of children within our organizer
        @rtype: list

        >>> 'Discovered' in dmd.Devices.childIds()
        True
        """
        if spec is None:
            spec = self.meta_type
            #spec = self.getDefaultSpecForChildren()
        return self.objectIds(spec=spec)


    security.declareProtected(ZEN_COMMON, "countChildren")
    def countChildren(self, spec=None):
        """
        Returns the number of all the children underneath an organizer

        @param spec: If set, returns children of the specified meta_type.
        @type spec: string
        @return: A count of all our contained children.
        @rtype: integer
        @permission: ZEN_COMMON

        """
        if spec is None:
            spec = self.meta_type
            #spec = self.getDefaultSpecForChildren()
        count = len(self.objectIds(spec=spec))
        for child in self.children(spec=spec):
            count += child.countChildren(spec=spec)
        return count


    security.declareProtected(ZEN_ADD, 'manage_addOrganizer')
    def manage_addOrganizer(self, newPath, factory=None, REQUEST=None):
        """
        Adds a new organizer under this organizer. if given a fully qualified
        path it will create an organizer at that path

        @param newPath: Path of the organizer to be created
        @type newPath:  string
        @raise: ZentinelException
        @permission: ZEN_ADD

        >>> dmd.Devices.manage_addOrganizer('/Devices/DocTest')
        """
        if factory is None:
            factory = self.__class__
        if not newPath: return self.callZenScreen(REQUEST)
        try:
            if newPath.startswith("/"):
                org = self.createOrganizer(newPath)
            else:
                # Strip out invalid characters from the newPath
                name = newPath
                newPath = self.prepId(newPath)
                org = factory(newPath)
                self._setObject(org.id, org)
                # Set the display name to the original string
                org = self._getOb(newPath)
                org.setTitle(name)
        except ZentinelException as e:
            if REQUEST:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error', e, priority=messaging.WARNING)
                return self.callZenScreen(REQUEST)
        if REQUEST:
            audit(('UI', getDisplayType(org), 'Add'), org)
            messaging.IMessageSender(self).sendToBrowser(
                'Organizer Added',
                '%s "%s" was created.' % (getDisplayType(self), newPath)
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_DELETE, 'manage_deleteOrganizer')
    def manage_deleteOrganizer(self, orgname, REQUEST=None):
        """
        Deletes an organizer underneath this organizer

        @param orgname: Name of the organizer to delete
        @type orgname: string
        @raise: KeyError
        @permission: ZEN_DELETE

        >>> dmd.Devices.manage_deleteOrganizer('/Devices/Server/Linux')
        """
        if REQUEST:
            audit(('UI', getDisplayType(self), 'Delete'), orgname)
        if orgname.startswith("/"):
            try:
                orgroot = self.getDmdRoot(self.dmdRootName)
                organizer = orgroot.getOrganizer(orgname)
                parent = aq_parent(organizer)
                parent._delObject(organizer.getId())
            except KeyError:
                pass  # we may have already deleted a sub object
        else:
            self._delObject(orgname)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Organizer Deleted',
                '%s "%s" was deleted.' % (getDisplayType(self), orgname)
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_DELETE, 'manage_deleteOrganizers')
    def manage_deleteOrganizers(self, organizerPaths=None, REQUEST=None):
        """
        Delete a list of Organizers from the database using their ids.

        @param organizerPaths: Names of organizer to be deleted
        @type organizerPaths: list
        @permission: ZEN_DELETE

        >>> dmd.Devices.manage_deleteOrganizers(['/Devices/Server/Linux',
        ... '/Devices/Server/Windows'])
        """
        if not organizerPaths:
            messaging.IMessageSender(self).sendToBrowser(
                'Error',
                'No organizers were specified.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        for organizerName in organizerPaths:
            if REQUEST:
                audit(('UI',getDisplayType(self),'Delete'), organizerName)
            self.manage_deleteOrganizer(organizerName)
        if REQUEST:
            plural = ''
            if len(organizerPaths) > 1: plural = 's'
            messaging.IMessageSender(self).sendToBrowser(
                'Organizers Deleted',
                '%s%s %s were deleted.' % (getDisplayType(self),
                                    plural, ', '.join(organizerPaths))
            )
            return self.callZenScreen(REQUEST)

    def deviceMoveTargets(self):
        """
        DEPRECATED - see childMoveTargets
        Return list of all organizers excluding our self.

        @return: A sorted list of organizers excluding our self.
        @rtype: list
        @todo: We should be using either deviceMoveTargets or childMoveTargets
        """
        targets = filter(lambda x: x != self.getOrganizerName(),
                self.getDmdRoot(self.dmdRootName).getOrganizerNames())
        return sorted(targets, key=lambda x: x.lower())


    def moveOrganizer(self, moveTarget, organizerPaths=None, REQUEST=None):
        """
        Move organizers under this organizer to another organizer

        @param moveTarget: Name of the destination organizer
        @type moveTarget: string
        @param organizerPaths: Paths of organizers to be moved
        @type organizerPaths: list

        >>> dmd.Events.Status.moveOrganizer('/Events/Ignore',
        ... ['Ping', 'Snmp'])
        """
        if not moveTarget or not organizerPaths: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        movedStuff = False
        for organizerName in organizerPaths:
            if moveTarget.find(organizerName) > -1: continue
            obj = self._getOb(organizerName, None)
            if obj is None: continue
            obj._operation = 1 #move object
            self._delObject(organizerName)
            target._setObject(organizerName, obj)
            movedStuff = True
        if REQUEST:
            if movedStuff:
                plural = ''
                if len(organizerPaths) > 1: plural = 's'
                for organizerName in organizerPaths:
                    audit(('UI', getDisplayType(self), 'Move'), organizerName, data_={'from':getDisplayName(self), 'to':getDisplayName(target)})
                messaging.IMessageSender(self).sendToBrowser(
                    'Organizers Moved',
                    '%s%s %s were moved to %s.' % (getDisplayType(self),
                                plural, ', '.join(organizerPaths), moveTarget)
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Error',
                    'No %s were moved.' % getDisplayType(self),
                    priority=messaging.WARNING
                )
            return target.callZenScreen(REQUEST)


    def createOrganizer(self, path):
        """
        Creates an organizer with a specified path.
        Use manage_addOrganizer instead

        @param path: Path of the organizer to create
        @type path: string
        @return: Organizer created with the specified path
        @rtype: Organizer
        """
        return self.createHierarchyObj(self.getDmdRoot(self.dmdRootName),
                                           path,self.__class__)


    def getOrganizer(self, path):
        """
        Get an organizer by path under the same root

        @param path: Path of the organizer to retrieve
        @type path: string
        @return: Organizer with the specified path
        @rtype: Organizer

        >>> dmd.Events.Status.getOrganizer('/Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        >>> dmd.Events.Status.getOrganizer('Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        >>> dmd.Events.Status.getOrganizer('/Events/Status/Snmp')
        <EventClass at /zport/dmd/Events/Status/Snmp>
        """
        # call prepId for each segment.
        path = '/'.join(self.prepId(s) for s in path.lstrip('/').split('/'))
        return self.getDmdRoot(self.dmdRootName).unrestrictedTraverse(path)


    security.declareProtected(ZEN_COMMON, "getOrganizerName")
    def getOrganizerName(self):
        """
        Return the DMD path of an Organizer without its dmdSubRel names.

        @return: Name of this organizer
        @rtype: string
        @permission: ZEN_COMMON

        >>> dmd.Events.Status.Snmp.getOrganizerName()
        '/Status/Snmp'
        """
        return self.getPrimaryDmdId(self.dmdRootName)
    getDmdKey = getOrganizerName


    security.declareProtected(ZEN_COMMON, "getOrganizerNames")
    def getOrganizerNames(self, addblank=False, checkPerm=True):
        """
        Returns a list of all organizer names under this organizer

        @param addblank: If True, add a blank item in the list.
        @type addblank: boolean
        @return: The DMD paths of all Organizers below this instance.
        @rtype: list
        @permission: ZEN_COMMON

        >>> dmd.Events.Security.getOrganizerNames()
        ['/Security', '/Security/Auth', '/Security/Conn',
        '/Security/Conn/Close', '/Security/Conn/Open', '/Security/Login',
        '/Security/Login/BadPass', '/Security/Login/Fail', '/Security/Sudo',
        '/Security/Virus']
        """
        groupNames = []
        user = getSecurityManager().getUser()
        if user.has_permission(ZEN_VIEW, self) or not checkPerm:
            groupNames.append(self.getOrganizerName())
        for subgroup in self.children(checkPerm=False):
            groupNames.extend(subgroup.getOrganizerNames())
        if self.id == self.dmdRootName:
            if addblank: groupNames.append("")
        groupNames.sort(key=lambda x: x.lower())
        return groupNames


    def _getCatalog(self):
        """
        Returns a catalog instance for this organizer.

        @return: The catalog instance for this Organizer.
        @rtype: ZCatalog
        @note: Catalog is found using the attribute default_catalog.
        """
        catalog = None
        if hasattr(self, self.default_catalog):
            catalog = getattr(self, self.default_catalog)
        return catalog


    security.declareProtected(ZEN_COMMON, "getSubOrganizers")
    def getSubOrganizers(self):
        """
        Returns all the organizers under this organizer

        @return: Organizers below this instance
        @rtype: list
        @permission: ZEN_COMMON

        >>> dmd.Events.Security.getSubOrganizers()
        [<EventClass at /zport/dmd/Events/Security/Login>,
        <EventClass at /zport/dmd/Events/Security/Sudo>,
        <EventClass at /zport/dmd/Events/Security/Conn>,
        <EventClass at /zport/dmd/Events/Security/Virus>,
        <EventClass at /zport/dmd/Events/Security/Auth>,
        <EventClass at /zport/dmd/Events/Security/Login/BadPass>,
        <EventClass at /zport/dmd/Events/Security/Login/Fail>,
        <EventClass at /zport/dmd/Events/Security/Conn/Open>,
        <EventClass at /zport/dmd/Events/Security/Conn/Close>]
        """
        orgs = self.children()
        for child in self.children():
            orgs.extend(child.getSubOrganizers())
        return orgs

    security.declareProtected(ZEN_COMMON, "getSubInstances")
    def getSubInstanceIds(self, rel):
        """
        Returns the object ids of all the instances of a specific relation
        under this organizer

        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object ids of instances under an relation of this org
        @rtype: list
        @raise: AttributeError
        @permission: ZEN_COMMON

        >>> dmd.Events.Security.Login.getSubInstanceIds('instances')
        ['MSExchangeIS Mailbox Store_1009', 'MSExchangeIS Mailbox Store_1011',
        'defaultmapping', 'dropbear', 'sshd', 'MSFTPSVC_100', 'W3SVC_100',
        'dropbear', 'remote(pam_unix)']
        """
        relobj = getattr(self, rel, None)
        if not relobj:
            raise AttributeError( "%s not found on %s" % (rel, self.id) )
        objs = relobj.objectIds()
        for suborg in self.children():
            objs.extend(suborg.getSubInstanceIds(rel))
        return objs

    security.declareProtected(ZEN_COMMON, "getSubInstances")
    def getSubInstances(self, rel):
        """
        Returns the object isntances of a specific relation
        under this organizer

        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object instances under an relation of this org
        @rtype: list
        @raise: AttributeError
        @permission: ZEN_COMMON

        >>> dmd.Events.Security.Login.getSubInstances('instances')
        [<EventClassInst at /zport/dmd/Events/Security/Login/instances/MSExchangeIS Mailbox Store_1009>,
        <EventClassInst at /zport/dmd/Events/Security/Login/instances/MSExchangeIS Mailbox Store_1011>,
        <EventClassInst at /zport/dmd/Events/Security/Login/instances/defaultmapping>,
        <EventClassInst at /zport/dmd/Events/Security/Login/BadPass/instances/dropbear>,
        <EventClassInst at /zport/dmd/Events/Security/Login/BadPass/instances/sshd>,
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/MSFTPSVC_100>,
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/W3SVC_100>,
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/dropbear>,
        <EventClassInst at /zport/dmd/Events/Security/Login/Fail/instances/remote(pam_unix)>]
        """
        relobj = getattr(self, rel, None)
        if not relobj:
            raise AttributeError( "%s not found on %s" % (rel, self.id) )
        objs = relobj()
        if not objs: objs = []
        for suborg in self.children():
            objs.extend(suborg.getSubInstances(rel))
        return objs

    security.declareProtected(ZEN_COMMON, "getSubInstancesGen")
    def getSubInstancesGen(self, rel):
        """
        Returns the object isntances of a specific relation
        under this organizer

        @param rel: The name of the relation to traverse
        @type rel: string
        @return: The object ids of instances under an relation of this org
        @rtype: generator
        @raise: AttributeError
        @permission: ZEN_COMMON
        """
        relobj = getattr(self, rel, None)
        if not relobj:
            raise AttributeError( "%s not found on %s" % (rel, self.id) )
        for obj in relobj.objectValuesGen():
            yield obj
        for suborg in self.children():
            for obj in suborg.getSubInstancesGen(rel):
                yield obj

    def exportXmlHook(self, ofile, ignorerels):
        """
        Calls exportXml on the children of this organizer

        @param ofile: The file to output
        @type ofile: File
        @param ignorerels: Relations to ignore
        @type ignorerels: list
        """
        map(lambda o: o.exportXml(ofile, ignorerels), self.children())


InitializeClass(Organizer)
