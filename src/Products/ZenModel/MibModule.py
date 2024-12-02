##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from AccessControl import ClassSecurityInfo, Permissions
from AccessControl.class_init import InitializeClass
from zExceptions import BadRequest
from zope.interface import implementer

from Products.ZenRelations.RelSchema import ToOne, ToManyCont
from Products.ZenWidgets import messaging

from .interfaces import IIndexed
from .MibNode import MibNode
from .MibNotification import MibNotification
from .ZenModelRM import ZenModelRM
from .ZenPackable import ZenPackable


def createOID(dmd, container, new_node, logger=None):
    for brain in dmd.mibSearch(oid=new_node.oid):
        old_node = dmd.unrestrictedTraverse(brain.getPath(), None)
        if old_node is None:
            # Brain's path not found, so delete it.
            dmd.mibSearch.uncatalog_object(brain.getPath())
            continue
        if logger and (old_node.moduleName != new_node.moduleName):
            logger.warn(
                "OID '%s' will be removed from organizer '%s' "
                "and added to organizer '%s'.",
                new_node.oid,
                old_node.moduleName,
                new_node.moduleName,
            )
        old_node.getParentNode()._delObject(old_node.id)
    try:
        container._checkId(new_node.id)
    except BadRequest:
        container._delObject(new_node.id)
    container._setObject(new_node.id, new_node)
    return container._getOb(new_node.id)


@implementer(IIndexed)
class MibModule(ZenModelRM, ZenPackable):
    types = ("COUNTER", "GAUGE", "DERIVE", "ABSOLUTE")

    language = ""
    contact = ""
    description = ""

    _properties = (
        {"id": "language", "type": "string", "mode": "w"},
        {"id": "contact", "type": "string", "mode": "w"},
        {"id": "description", "type": "string", "mode": "w"},
    )

    _relations = ZenPackable._relations + (
        (
            "miborganizer",
            ToOne(ToManyCont, "Products.ZenModel.MibOrganizer", "mibs"),
        ),
        ("nodes", ToManyCont(ToOne, "Products.ZenModel.MibNode", "module")),
        (
            "notifications",
            ToManyCont(ToOne, "Products.ZenModel.MibNotification", "module"),
        ),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            "immediate_view": "viewMibModule",
            "actions": (
                {
                    "id": "overview",
                    "name": "Overview",
                    "action": "viewMibModule",
                    "permissions": (Permissions.view,),
                },
                {
                    "id": "edit",
                    "name": "Edit",
                    "action": "editMibModule",
                    "permissions": (Permissions.view,),
                },
            ),
        },
    )

    security = ClassSecurityInfo()

    def getModuleName(self):
        return self.id

    def nodeCount(self):
        return self.nodes.countObjects()

    def notificationCount(self):
        return self.notifications.countObjects()

    def deleteMibNodes(self, ids, REQUEST=None):
        """
        Delete MibNodes

        @type ids: Sequence[str]
        """
        for node in self.nodes():
            id = getattr(node, "id", None)
            if id in ids:
                self.nodes._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Mappings Deleted", "Mib nodes deleted: %s" % (", ".join(ids))
            )
            return self.callZenScreen(REQUEST)

    def addMibNode(self, id, oid, nodetype, REQUEST=None):
        """Add a MibNode"""
        node = self.createMibNode(
            id, oid=oid, nodetype=nodetype, moduleName=self.id
        )
        if REQUEST:
            if node:
                messaging.IMessageSender(self).sendToBrowser(
                    "Mib Node Added",
                    "Node %s was created with oid %s." % (id, oid),
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    "Invalid OID",
                    "OID %s is invalid." % oid,
                    priority=messaging.WARNING,
                )
            return self.callZenScreen(REQUEST)

    def createMibNode(self, id, logger=None, **kwargs):
        """Create a MibNotification"""
        return createOID(self.dmd, self.nodes, MibNode(id, **kwargs), logger)

    def deleteMibNotifications(self, ids, REQUEST=None):
        """
        Delete MibNotifications

        @type ids: Sequence[str]
        """
        for notification in self.notifications():
            id = getattr(notification, "id", None)
            if id in ids:
                self.notifications._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                "Traps Deleted", "Traps deleted: %s" % (", ".join(ids))
            )
            return self.callZenScreen(REQUEST)

    def addMibNotification(self, id, oid, nodetype, REQUEST=None):
        """Add a MibNotification"""
        notification = self.createMibNotification(
            id, oid=oid, nodetype=nodetype, moduleName=self.id
        )
        if REQUEST:
            if notification:
                messaging.IMessageSender(self).sendToBrowser(
                    "Trap added",
                    "Trap %s was created with oid %s." % (id, oid),
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    "Invalid OID",
                    "OID %s is invalid." % oid,
                    priority=messaging.WARNING,
                )
            return self.callZenScreen(REQUEST)

    def createMibNotification(self, id, logger=None, **kwargs):
        """Create a MibNotification"""
        return createOID(
            self.dmd, self.notifications, MibNotification(id, **kwargs), logger
        )


InitializeClass(MibModule)
