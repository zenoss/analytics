##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.Lockable import Lockable
from Products.ZenModel.OSProcessMatcher import OSProcessMatcher
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging
from Acquisition import aq_chain
from Lockable import UNLOCKED, DELETE_LOCKED, UPDATE_LOCKED
from OSComponent import OSComponent
from ZenPackable import ZenPackable
from Products.ZenUtils.Utils import prepId
from persistent.list import PersistentList
import logging

log = logging.getLogger("zen.osprocess")

def manage_addOSProcess(context, newClassName, example, userCreated, REQUEST=None):
    """
    Make an os process from the ZMI
    """
    pc = context.unrestrictedTraverse(newClassName)
    if pc.matches(example):
        name = pc.generateName(example)
        id = pc.generateIdFromName(name)
        p = OSProcess(id)
        p.displayName = name
        p.__of__(context).setOSProcessClass(newClassName)
        context._setObject(id, p)
        p = context._getOb(id)
        if userCreated: p.setUserCreateFlag()
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')
        return p
    else:
        msg = "Invalid example. Process Class '%s' would not capture it" % pc.name
        raise ValueError(msg)

class OSProcess(OSComponent, Commandable, ZenPackable, OSProcessMatcher):
    """
    OSProcess object
    """
    portal_type = meta_type = 'OSProcess'

    @property
    def includeRegex(self):
        return self.osProcessClass().includeRegex

    @property
    def excludeRegex(self):
        return self.osProcessClass().excludeRegex

    @property
    def replaceRegex(self):
        return self.osProcessClass().replaceRegex

    @property
    def replacement(self):
        return self.osProcessClass().replacement

    def processClassPrimaryUrlPath(self):
        return self.osProcessClass().getPrimaryUrlPath()

    @property
    def generatedId(self):
        return self.id

    displayName = ""
    minProcessCount = ""
    maxProcessCount = ""
    minProcessMemory = ""
    maxProcessMemory = ""
    monitoredProcesses = PersistentList()

    modelerLock = None
    sendEventWhenBlockedFlag = None

    collectors = ('zenprocess','zencommand')

    _properties = OSComponent._properties + (
        {'id':'displayName', 'type':'string', 'mode':'w'},
        {'id':'minProcessCount', 'type':'int', 'mode':'w'},
        {'id':'maxProcessCount', 'type':'int', 'mode':'w'},
        {'id':'minProcessMemory', 'type':'int', 'mode':'w'},
        {'id':'maxProcessMemory', 'type':'int', 'mode':'w'},
        {'id':'includeRegex', 'type':'string', 'mode':'w'},
        {'id':'excludeRegex', 'type':'string', 'mode':'w'},
        {'id':'replaceRegex', 'type':'string', 'mode':'w'},
        {'id':'replacement', 'type':'string', 'mode':'w'},
    )

    _relations = OSComponent._relations + ZenPackable._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "processes")),
        ("osProcessClass", ToOne(ToMany, "Products.ZenModel.OSProcessClass", "instances")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
    )

    security = ClassSecurityInfo()


    def getMonitoredProcesses(self):
        """
        return monitoredProcesses
        """
        return self.monitoredProcesses

    
    def setMonitoredProcesses(self, monitoredProcesses):
        """
        @parameter monitoredProcesses: a list that has been converted to a MultiArgs of monitored processes
        @type monitoredProcesses:: MultiArgs
        """
        self.monitoredProcesses = monitoredProcesses.args[0]


    def getOSProcessConf(self):
        """
        Return information used to monitor this process.
        """
        return (self.id, self.alertOnRestart(), self.getFailSeverity())


    def setOSProcessClass(self, procKey):
        """
        Set the OSProcessClass based on procKey which is the proc + args.
        We set by matching regular expressions of each proces class.
        """
        klass = self.getDmdObj(procKey)
        klass.instances.addRelation(self)


    def getOSProcessClass(self):
        """
        Return the current procKey.
        """
        pClass = self.osProcessClass()
        if pClass:
            return pClass.getPrimaryDmdId()


    def getOSProcessClassLink(self):
        """
        Return a link to the OSProcessClass.
        """
        proccl = self.osProcessClass()
        if proccl:
            if self.checkRemotePerm("View", proccl):
                return "<a href='%s'>%s</a>" % (proccl.getPrimaryUrlPath(),
                                                proccl.getOSProcessClassName())
            else:
                return proccl.getOSProcessClassName()
        return ""

    def getMinProcessCount(self):
        """
        Return the min process count threshold value
        """
        if not self.minProcessCount and not self.maxProcessCount \
            and not self.osProcessClass().minProcessCount \
            and self.osProcessClass().getPrimaryParent():
            try:
                value = self.osProcessClass().getPrimaryParent().minProcessCount
            except AttributeError:
                value = None
        elif not self.minProcessCount and not self.maxProcessCount \
            and self.osProcessClass():
            value = self.osProcessClass().minProcessCount
        else:
            value = self.minProcessCount

        return float(value) if value else None

    def getMaxProcessCount(self):
        """
        Return the max process count threshold value
        """
        if not self.minProcessCount and not self.maxProcessCount \
            and not self.osProcessClass().maxProcessCount \
            and self.osProcessClass().getPrimaryParent():
            try:
                value = self.osProcessClass().getPrimaryParent().maxProcessCount
            except AttributeError:
                value = None
        elif not self.minProcessCount and not self.maxProcessCount \
            and self.osProcessClass():
            value = self.osProcessClass().maxProcessCount
        else:
            value = self.maxProcessCount

        return float(value) if value else None

    def getMinProcessMemory(self):
        """
        Return the min process memory threshold value
        """
        if not self.minProcessMemory and not self.maxProcessMemory \
            and not self.osProcessClass().minProcessMemory \
            and self.osProcessClass().getPrimaryParent():
            try:
                value = self.osProcessClass().getPrimaryParent().minProcessMemory
            except AttributeError:
                value = None
        elif not self.minProcessMemory and not self.maxProcessMemory \
            and self.osProcessClass():
            value = self.osProcessClass().minProcessMemory
        else:
            value = self.minProcessMemory

        return float(value) if value else None

    def getMaxProcessMemory(self):
        """
        Return the max process memory threshold value
        """
        if not self.maxProcessMemory and not self.minProcessMemory \
            and not self.osProcessClass().maxProcessMemory \
            and self.osProcessClass().getPrimaryParent():
            try:
                value = self.osProcessClass().getPrimaryParent().maxProcessMemory
            except AttributeError:
                value = None
        elif not self.maxProcessMemory and not self.minProcessMemory \
            and self.osProcessClass():
            value = self.osProcessClass().maxProcessMemory
        else:
            value = self.maxProcessMemory

        return float(value) if value else None

    def getTitleOrId(self):
        if self.osProcessClass():
            return self.osProcessClass().titleOrId()
        return self.title() or self.id

    def name(self):
        """
        Return a string that describes the process set
        (Perhaps, simply the process name + parameters)
        """
        return getattr(self,'displayName',None)

    title = name


    def monitored(self):
        """
        Should this service be monitored or not. Use ServiceClass aq path.
        """
        return self.getAqProperty("zMonitor")


    def alertOnRestart(self):
        """
        Retrieve the zProperty zAlertOnRestart
        """
        return self.getAqProperty("zAlertOnRestart")


    def getSeverities(self):
        """
        Return a list of tuples with the possible severities
        """
        return self.ZenEventManager.getSeverities()


    def getFailSeverity(self):
        """
        Return the severity for this service when it fails.
        """
        return self.getAqProperty("zFailSeverity")


    def getFailSeverityString(self):
        """
        Return a string representation of zFailSeverity
        """
        return self.ZenEventManager.severities[self.getAqProperty("zFailSeverity")]


    def getClassObject(self):
        """
        Return the ProcessClass for this proc
        """
        return self.osProcessClass()


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_editOSProcess')
    def manage_editOSProcess(self, zMonitor=False, zAlertOnRestart=False,
                             zFailSeverity=3, msg=None,REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if msg is None: msg=[]
        msg.append(self.setAqProperty("zMonitor", zMonitor, "boolean"))
        msg.append(self.setAqProperty("zAlertOnRestart",zAlertOnRestart,"int"))
        msg.append(self.setAqProperty("zFailSeverity",zFailSeverity,"int"))
        msg = [ m for m in msg if m ]
        self.index_object()
        if not msg: msg.append("No action needed")
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Process Edited',
                ", ".join(msg) + ":"
            )
            return self.callZenScreen(REQUEST)


    def getUserCommandTargets(self):
        '''
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return [self]


    def getUserCommandEnvironment(self):
        """
        Return the environment to be used when processing a UserCommand
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'proc': context,  'process': context,})
        return environ


    def getAqChainForUserCommands(self):
        """
        Setup the aq chain as appropriate for the execution of a UserCommand
        """
        chain = aq_chain(self.getClassObject().primaryAq())
        chain.insert(0, self)
        return chain


    def getUrlForUserCommands(self):
        """
        Return the url where UserCommands are viewed for this object
        """
        return self.getPrimaryUrlPath() + '/osProcessManage'

    # override the lock methods to look for the process classes'
    # lock state instead of the current object if it has not been set

    def _getSendEventWhenBlockedFlag(self):
        if self.sendEventWhenBlockedFlag is None and self.osProcessClass():
            return self.osProcessClass().primaryAq().getZ("zSendEventWhenBlockedFlag")
        return self.sendEventWhenBlockedFlag

    security.declareProtected(ZEN_MANAGE_DMD, 'sendEventWhenBlocked')
    def sendEventWhenBlocked(self):
        return self._getSendEventWhenBlockedFlag()

    def _getModelerLock(self):
        if self.modelerLock is None and self.osProcessClass():
            return self.osProcessClass().primaryAq().getZ("zModelerLock")
        return self.modelerLock

    def isUnlocked(self):
        return self._getModelerLock() == UNLOCKED

    def isLockedFromDeletion(self):
        lock = self._getModelerLock()
        return (lock == DELETE_LOCKED
                or lock == UPDATE_LOCKED)

    def isLockedFromUpdates(self):
        return self._getModelerLock() == UPDATE_LOCKED

    def _checkLockProperties(self):
        """
        If we are reseting the locking properties of a process
        to the same as the class then delete the local copy.

        This means that if you override a process instance to have
        a locking policy different then its parent, but then change your
        mind and reset it to the parents it will update with the parents.
        """
        if self.osProcessClass():
            pclass = self.osProcessClass().primaryAq()
            if pclass.getZ("zModelerLock") == self.modelerLock:
                self.modelerLock = None
                # if they reset the modeler lock see if we can reset the
                # send flag as well
                if pclass.getZ("zSendEventWhenBlockedFlag") == self.sendEventWhenBlockedFlag:
                    self.sendEventWhenBlockedFlag = None

    security.declareProtected(ZEN_MANAGE_DMD, 'unlock')
    def unlock(self, REQUEST=None):
        Lockable.unlock(self, REQUEST=REQUEST)
        self._checkLockProperties()

    security.declareProtected(ZEN_MANAGE_DMD, 'lockFromDeletion')
    def lockFromDeletion(self, sendEventWhenBlocked=None, REQUEST=None):
        Lockable.lockFromDeletion(self, sendEventWhenBlocked=sendEventWhenBlocked, REQUEST=REQUEST)
        self._checkLockProperties()

    security.declareProtected(ZEN_MANAGE_DMD, 'lockFromUpdates')
    def lockFromUpdates(self, sendEventWhenBlocked=None, REQUEST=None):
        Lockable.lockFromUpdates(self, sendEventWhenBlocked=sendEventWhenBlocked, REQUEST=REQUEST)
        self._checkLockProperties()


InitializeClass(OSProcess)
