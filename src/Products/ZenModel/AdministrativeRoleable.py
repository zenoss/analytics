##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""
AdministrativeRoleable.py

Created by Marc Irlandez on 2007-04-05.
"""

from AccessControl import ClassSecurityInfo
from Products.ZenMessaging.audit import audit
from Products.ZenModel.AdministrativeRole import AdministrativeRole
from AccessControl.class_init import InitializeClass
from zope.event import notify
from Products.ZenUtils.Utils import getDisplayType
from Products.Zuul.catalog.events import IndexingEvent
from ZenossSecurity import *
from Products.ZenWidgets import messaging

class AdministrativeRoleable:

    security = ClassSecurityInfo()

    security.declareProtected(ZEN_ADMINISTRATORS_VIEW,
        'getAdministrativeRoles')
    def getAdministrativeRoles(self):
        "Get the Admin Roles on this device"
        return self.adminRoles.objectValuesAll()

    security.declareProtected(ZEN_ADMINISTRATORS_EDIT,
        'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, newId=None, REQUEST=None):
        "Add a Admin Role to this device"
        us = self.ZenUsers.getUserSettings(newId)
        AdministrativeRole(us, self)
        self.setAdminLocalRoles()
        self.index_object()
        notify(IndexingEvent(self))
        if REQUEST:
            if us:
                audit(['UI', getDisplayType(self), 'AddAdministrativeRole'], self, newId=newId)
                messaging.IMessageSender(self).sendToBrowser(
                    'Admin Role Added',
                    'The %s administrative role has been added.' % newId
                )
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_ADMINISTRATORS_EDIT,
        'manage_editAdministrativeRoles')
    def manage_editAdministrativeRoles(self, ids=(), role=(), REQUEST=None):
        """
        Edit list of admin roles.
        """
        if isinstance(ids, basestring):
            ids = [ids]
            role = [role]

        editedRoles = []
        for i, id in enumerate(ids):
            roleEdit = (id, role[i])
            editedRoles.append(roleEdit)
            ar = self.adminRoles._getOb(roleEdit[0])
            ar.update(roleEdit[1])

        self.setAdminLocalRoles()
        self.index_object()
        notify(IndexingEvent(self))
        if REQUEST:
            for roleEdit in editedRoles:
                audit(['UI', getDisplayType(self), 'EditAdministrativeRole'], self,
                      id=roleEdit[0], role=roleEdit[1])
            messaging.IMessageSender(self).sendToBrowser(
                'Admin Roles Updated',
                ('The following administrative roles have been updated: '
                 '%s' % ", ".join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_ADMINISTRATORS_EDIT,
        'manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        if isinstance(delids, basestring):
            delids = [delids]
        for userid in delids:
            ar = self.adminRoles._getOb(userid, None)
            if ar is not None: ar.delete()
            self.manage_delLocalRoles((userid,))
        self.setAdminLocalRoles()
        self.index_object()
        notify(IndexingEvent(self))
        if REQUEST:
            if delids:
                for userid in delids:
                    audit(['UI', getDisplayType(self), 'DeleteAdministrativeRole'], self, userid=userid)
                messaging.IMessageSender(self).sendToBrowser(
                    'Admin Roles Deleted',
                    ('The following administrative roles have been deleted: '
                     '%s' % ", ".join(delids))
                )
            return self.callZenScreen(REQUEST)

    def manage_listAdministrativeRoles(self):
        """List the user and their roles on an object"""
        return [ (ar.id, (ar.role,)) for ar in self.adminRoles() ]


    def setAdminLocalRoles(self):
        """Hook for setting permissions"""
        pass


InitializeClass(AdministrativeRoleable)
