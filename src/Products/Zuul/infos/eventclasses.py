##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
log = logging.getLogger("zen.Events")
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase, ProxyProperty
from Products.Zuul.interfaces import IEventClassTreeNode, IEventClassInfo, IEventClasses, IInfo
from Products.ZenEvents.EventClass import EventClass


class EventClassTreeNode(TreeNode):
    implements(IEventClassTreeNode)
    adapts(EventClass)
    count = 0

    @property
    def children(self):
        obj = self._get_object()
        orgs = obj.children()
        orgs = sorted(orgs, key=lambda org: org.titleOrId())
        return [EventClassTreeNode(o) for o in orgs]

    @property
    def leaf(self):
        obj = self._get_object()
        if obj.children():
            return False
        return True

    def _count_children(self):
        for child in self.children:
            self.count += 1
            self.count += child._count_children()
        return self.count

    def _checkTransform(self):
        obj = self._object.getObject()
        if obj.transform:
            return True
        else:
            return False

    @property
    def text(self):
        self.count = 0
        numInstances = self._count_children()
        hasTransform = self._checkTransform()
        text = super(EventClassTreeNode, self).text
        obj = self._object.getObject()
        desc = obj.description
        return {
            'text': text,
            'count': numInstances,
            'description': desc,
            'hasTransform': hasTransform
        }

class EventClassInfo(InfoBase):
    implements(IEventClassInfo)
    adapts(IEventClasses)

    eventClassKey   = ProxyProperty('eventClassKey')
    evaluation      = ProxyProperty('explanation')
    example         = ProxyProperty('example')
    rule            = ProxyProperty('rule')
    regex           = ProxyProperty('regex')
    sequence        = ProxyProperty('sequence')
    resolution      = ProxyProperty('resolution')
    transform       = ProxyProperty('transform')

    @property
    def getEventStatus(self):
        return self._object.getStatus()

    @property
    def ruleOrRegex(self):
        return self._object.ruleOrRegex()
