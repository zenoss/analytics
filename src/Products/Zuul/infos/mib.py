##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from itertools import imap, chain

from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.interfaces import IMibInfo, IMibOrganizerNode, IMibNode
from Products.Zuul.interfaces import (
    IMibOrganizerInfo, IMibNodeInfo, IMibNotificationInfo
)
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.ZenModel.MibOrganizer import MibOrganizer
from Products.ZenModel.MibModule import MibModule
from Products.ZenModel.MibBase import MibBase


class MibOrganizerNode(TreeNode):
    implements(IMibOrganizerNode)
    adapts(MibOrganizer)

    @property
    def text(self):
        text = super(MibOrganizerNode, self).text
        count = IModelCatalogTool(self._object).count((MibModule,), self.uid)
        return {'text': text, 'count': count}

    @property
    def children(self):
        org = self._object.getObject()
        return chain(imap(MibOrganizerNode, org.children()),
                     imap(MibNode, org.mibs()))

    @property
    def leaf(self):
        return False

    @property
    def iconCls(self):
        return 'folder'

    @property
    def qtip(self):
        return self._object.description


class MibNode(TreeNode):
    """
    Nodes or traps are just subclasses of MibBase
    """
    implements(IMibNode)
    adapts(MibBase)

    def __init__(self, obj):
        TreeNode.__init__(self, obj)
        self._nodes = []

    def _addSubNode(self, node):
        self._nodes.append(node)

    @property
    def children(self):
        return self._nodes

    @property
    def text(self):
        obj = self._object.getObject()
        if hasattr(obj, 'oid'):
            return obj.oid + ' ' + self._object.id
        return self._object.id

    @property
    def oid(self):
        obj = self._object.getObject()
        if hasattr(obj, 'oid'):
            return obj.oid
        return ''

    @property
    def leaf(self):
        return len(self._nodes) == 0

    @property
    def iconCls(self):
        if self.leaf:
            return 'leaf'
        return 'folder'

    @property
    def qtip(self):
        return self._object.description


class FakeTopLevelNodeInfo(TreeNode):
    implements(IMibNode)

    def __init__(self, obj):
        TreeNode.__init__(self, obj)
        self._nodes = []
        self.qtip = "Top Level OID container"
        self.oid = ''

    def _addSubNode(self, node):
        self._nodes.append(node)

    @property
    def children(self):
        return self._nodes

    @property
    def text(self):
        return "Top Level OID container"

    @property
    def iconCls(self):
        return 'folder'


class MibInfoBase(InfoBase):
    pass


class MibNodeInfo(MibInfoBase):
    implements(IMibNodeInfo)

    @property
    def name(self):
        return self._object.getId()

    oid = ProxyProperty('oid')
    nodetype = ProxyProperty('nodetype')
    access = ProxyProperty('access')
    status = ProxyProperty('status')
    description = ProxyProperty('description')


class MibNotificationInfo(MibInfoBase):
    implements(IMibNotificationInfo)

    @property
    def name(self):
        return self._object.getId()

    oid = ProxyProperty('oid')
    nodetype = ProxyProperty('nodetype')

    @property
    def objects(self):
        return list(self._object.objects)

    status = ProxyProperty('status')
    description = ProxyProperty('description')


class MibInfo(MibInfoBase):
    implements(IMibInfo)

    @property
    def count(self):
        return 1

    @property
    def newId(self):
        return self._object.id

    language = ProxyProperty('language')
    contact = ProxyProperty('contact')
    description = ProxyProperty('description')


class MibOrganizerInfo(MibInfoBase):
    implements(IMibOrganizerInfo)
    adapts(MibOrganizer)
