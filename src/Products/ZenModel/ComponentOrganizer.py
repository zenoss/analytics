##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """ComponentOrganizer
Base class for all component organizers.
"""

import logging

from zope.event import notify
from zope.interface import implements
from AccessControl import ClassSecurityInfo
from ZODB.transact import transact
from AccessControl.class_init import InitializeClass

from Products.ZenModel.AdministrativeRoleable import AdministrativeRoleable
from Products.ZenModel.ZenossSecurity import ZEN_VIEW, ZEN_MANAGE_DMD
from Products.ZenModel.Organizer import Organizer
from Products.ZenModel.MaintenanceWindowable import MaintenanceWindowable
from Products.ZenRelations.RelSchema import ToOne, ToManyCont
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenWidgets import messaging
from Products.Zuul.catalog.events import IndexingEvent


LOG = logging.getLogger('zen.ComponentGroups.ComponentOrganizer')


class ComponentOrganizer(Organizer, AdministrativeRoleable, MaintenanceWindowable):
    """
    ComponentOrganizer is the base class for all component organizers.
    """

    implements(IGloballyIdentifiable)

    security = ClassSecurityInfo()

    _relations = Organizer._relations + (
        ("maintenanceWindows", ToManyCont(
            ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(
            ToOne, "Products.ZenModel.AdministrativeRole", "managedObject")),
    )

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

    def index_object(self, idxs=None):
        """
        No action. Index of sub components will happen in
        manage_addAdministrativeRole.
        """
        pass

    def unindex_object(self):
        """
        No action. Unindex of sub components will happen in
        manage_deleteAdministrativeRole.
        """
        pass

    def _setComponentLocalRoles(self):
        def componentChunk(components, chunksize=10):
            i = 0
            maxi = len(components)
            while i < maxi:
                nexti = i+chunksize
                yield components[i:nexti]
                i = nexti

        @transact
        def setLocalRoles(components):
            for component in components:
                component = component.primaryAq()
                component.setAdminLocalRoles()

        components = self.components()
        total = len(components)
        count = 0
        for chunk in componentChunk(components):
            count += len(chunk)
            LOG.info("Setting admin roles on %d of total %d", count, total)
            setLocalRoles(chunk)

    security.declareProtected(ZEN_VIEW, 'getPrettyLink')
    def getPrettyLink(self, noicon=False, shortDesc=False):
        """ Gets a link to this object, plus an icon """
        href = self.getPrimaryUrlPath().replace('%', '%%')
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

    def manage_addAdministrativeRole(self, user_id, REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_addAdministrativeRole
        Adds an administrator to this ComponentOrganizer

        @param user_id: User to make an administrator of this Organizer
        @type user_id: string
        """

        AdministrativeRoleable.manage_addAdministrativeRole(self, user_id)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._setComponentLocalRoles()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                'Administrative role %s was added.' % user_id
            )

            return self.callZenScreen(REQUEST)

    def manage_editAdministrativeRoles(self, ids=(), role=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_editAdministrativeRoles
        Updates the administrators to this ComponentOrganizer

        @param ids: Users to update
        @type ids: tuple of strings
        """
        AdministrativeRoleable.manage_editAdministrativeRoles(self, ids, role)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._setComponentLocalRoles()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Role Added',
                'Administrative roles were updated: %s' % ', '.join(ids)
            )

            return self.callZenScreen(REQUEST)

    def manage_deleteAdministrativeRole(self, ids=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_deleteAdministrativeRole
        Deletes administrators to this ComponentOrganizer

        @param ids: Users to delete
        @type ids: tuple of strings
        """
        AdministrativeRoleable.manage_deleteAdministrativeRole(self, ids)
        notify(IndexingEvent(self, ('allowedRolesAndUsers',), False))
        self._setComponentLocalRoles()
        if REQUEST:
            if ids:
                messaging.IMessageSender(self).sendToBrowser(
                    'Roles Deleted',
                    'Administrative roles were deleted: %s' % ', '.join(ids)
                )

            return self.callZenScreen(REQUEST)


InitializeClass(ComponentOrganizer)
