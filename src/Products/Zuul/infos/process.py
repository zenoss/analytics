##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from zope.component import adapts
from zope.interface import implements
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.interfaces import IProcessEntity
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.utils import catalogAwareImap


class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    @property
    def iconCls(self):
        return ''

    @property
    def text(self):
        text = super(ProcessNode, self).text
        obj = self._object.getObject()
        count = obj.countClasses()
        return {
            'text': text,
            'count': count,
            'description': 'instances'
        }

    @property
    def children(self):
        orgs = self._object.getObject().children()
        orgs.sort(key=lambda x: x.titleOrId())
        return catalogAwareImap(lambda x:ProcessNode(x, self._root, self), orgs)

    @property
    def leaf(self):
        return 'osProcessClasses' in self.uid

class ProcessInfo(InfoBase):
    implements(IProcessInfo)
    adapts(IProcessEntity)

    def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)

    def setZMonitor(self, data):
        setZPropertyInfo(self._object, 'zMonitor', **data)
        process_classes = []
        if isinstance(self._object, OSProcessOrganizer):
            process_classes = self._object.getSubOSProcessClassesGen()
        elif isinstance(self._object, OSProcessClass):
            process_classes.append(self._object)

        def reindex_class(process_class):
            """
            Re-indexes a process class and its associated instances.
            """
            process_class.index_object()
            for proc in process_class.instances():
                proc.primaryAq().index_object()

        for process_class in process_classes:
            reindex_class(process_class)

    zMonitor = property(getZMonitor, setZMonitor)

    def getZAlertOnRestart(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAlertOnRestart', True, translate)

    def setZAlertOnRestart(self, data):
        setZPropertyInfo(self._object, 'zAlertOnRestart', **data)

    zAlertOnRestart = property(getZAlertOnRestart, setZAlertOnRestart)

    def getZFailSeverity(self):
        def translate(rawValue):
            return {5: 'Critical',
                    4: 'Error',
                    3: 'Warning',
                    2: 'Info',
                    1: 'Debug'}[rawValue]
        return getZPropertyInfo(self._object, 'zFailSeverity', 4, translate)

    def setZFailSeverity(self, data):
        setZPropertyInfo(self._object, 'zFailSeverity', **data)

    zFailSeverity = property(getZFailSeverity, setZFailSeverity)

    def getZModelerLock(self):
        def translate(rawValue):
            return {0: "Unlocked",
                    1: "Lock from Deletes",
                    2: "Lock from Updates"}[rawValue]
        return getZPropertyInfo(self._object, 'zModelerLock', 0, translate)

    def setZModelerLock(self, data):
        setZPropertyInfo(self._object, 'zModelerLock', **data)


    zModelerLock = property(getZModelerLock, setZModelerLock)

    def getZSendEventWhenBlockedFlag(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zSendEventWhenBlockedFlag', False, translate)

    def setZSendEventWhenBlockedFlag(self, data):
        setZPropertyInfo(self._object, 'zSendEventWhenBlockedFlag', **data)        

    zSendEventWhenBlockedFlag = property(getZSendEventWhenBlockedFlag, setZSendEventWhenBlockedFlag)

    def getHasRegex(self):
        return isinstance(self._object, OSProcessClass)

    def setHasRegex(self, hasRegex):
        pass

    hasRegex = property(getHasRegex, setHasRegex)

    def getIncludeRegex(self):
        return getattr(self._object, 'includeRegex', None) \
            or getattr(self._object, 'regex', None)

    def setIncludeRegex(self, includeRegex):
        if self.hasRegex:
            self._object.includeRegex = includeRegex

    includeRegex = property(getIncludeRegex, setIncludeRegex)
    regex = property(getIncludeRegex, setIncludeRegex)

    def getExcludeRegex(self):
        return getattr(self._object, 'excludeRegex', None)

    def setExcludeRegex(self, excludeRegex):
        if self.hasRegex:
            self._object.excludeRegex = excludeRegex

    excludeRegex = property(getExcludeRegex, setExcludeRegex)
    
    def getReplaceRegex(self):
        return getattr(self._object, 'replaceRegex', None)

    def setReplaceRegex(self, replaceRegex):
        if self.hasRegex:
            self._object.replaceRegex = replaceRegex

    replaceRegex = property(getReplaceRegex, setReplaceRegex)

    def getReplacement(self):
        return getattr(self._object, 'replacement', None)

    def setReplacement(self, replacement):
        if self.hasRegex:
            self._object.replacement = replacement

    replacement = property(getReplacement, setReplacement)

    def getMinProcessCount(self):
        return getattr(self._object, 'minProcessCount', '')

    def setMinProcessCount(self, minProcessCount):
        self._object.minProcessCount = minProcessCount

    minProcessCount = property(getMinProcessCount, setMinProcessCount)

    def getMaxProcessCount(self):
        return getattr(self._object, 'maxProcessCount', '')

    def setMaxProcessCount(self, maxProcessCount):
        self._object.maxProcessCount = maxProcessCount

    maxProcessCount = property(getMaxProcessCount, setMaxProcessCount)

    def getMinProcessMemory(self):
        return getattr(self._object, 'minProcessMemory', '')

    def setMinProcessMemory(self, minProcessMemory):
        self._object.minProcessMemory = minProcessMemory

    minProcessMemory = property(getMinProcessMemory, setMinProcessMemory)

    def getMaxProcessMemory(self):
        return getattr(self._object, 'maxProcessMemory', '')

    def setMaxProcessMemory(self, maxProcessMemory):
        self._object.maxProcessMemory = maxProcessMemory

    maxProcessMemory = property(getMaxProcessMemory, setMaxProcessMemory)

    @property
    def count(self):
        if isinstance(self._object, OSProcessOrganizer):
            return self._object.countClasses()
        # it is an instance
        return self._object.count()
