##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007-2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.OSProcessOrganizer")

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *
from Products.ZenModel.Lockable import UNLOCKED
from Acquisition import aq_base
from Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from ZenPackable import ZenPackable
from Organizer import Organizer
from OSProcessClass import OSProcessClass

def manage_addOSProcessOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = OSProcessOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

addOSProcessOrganizer = DTMLFile('dtml/addOSProcessOrganizer',globals())

class OSProcessOrganizer(Organizer, Commandable, ZenPackable):
    meta_type = "OSProcessOrganizer"
    dmdRootName = "Processes"
    #default_catalog = "osprocessSearch"

    description = ""

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations = Organizer._relations + ZenPackable._relations + (
        ("osProcessClasses", ToManyCont(
            ToOne,"Products.ZenModel.OSProcessClass","osProcessOrganizer")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )

    security = ClassSecurityInfo()

    def __init__(self, id=None, description=None):
        if not id: id = self.dmdRootName
        super(OSProcessOrganizer, self).__init__(id, description)
        if self.id == self.dmdRootName:
            self.buildZProperties()


    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = Organizer.zentinelTabs(self, templateName)
        if self.getPrimaryId() != '/zport/dmd/Processes':
            tabs = [t for t in tabs if t['id'] != 'resequence']
        return tabs


    def getSubOSProcessClassesGen(self):
        """Return generator that goes through all process classes.
        """
        for proc in self.osProcessClasses.objectValuesGen():
            yield proc
        for subgroup in self.children():
            for proc in subgroup.getSubOSProcessClassesGen():
                yield proc


    def getSubOSProcessClassesSorted(self):
        '''Return list of the process classes sorted by sequence.
        '''
        procs = sorted(self.getSubOSProcessClassesGen(),
                    key=lambda a: a.sequence)
        # reset sequence numbers to 0-n
        for i, p in enumerate(procs):
            p.sequence = i
        return procs

    def countClasses(self):
        """Count all osprocessclasses with in a ServiceOrganizer.
        """
        count = self.osProcessClasses.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    security.declareProtected(ZEN_ADD, 'manage_addOSProcessClass')
    def manage_addOSProcessClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = OSProcessClass(id)
            sc.sequence = len(self.osProcessClasses())
            self.osProcessClasses._setObject(id, sc)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        else:
            return self.osProcessClasses._getOb(id)


    def manage_resequenceProcesses(self, seqmap=(), origseq=(), REQUEST=None):
        "resequence the OsProcesses"
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.getSubOSProcessClassesGen(),
                            seqmap, origseq, REQUEST)

    def unmonitorOSProcessClasses(self, ids=None, REQUEST=None):
        return self.monitorOSProcessClasses(ids, False, REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'monitorOSProcessClasses')
    def monitorOSProcessClasses(self, ids=None, monitor=True, REQUEST=None):
        """Remove OSProcessClasses from an EventClass.
        """
        if not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        for id in ids:
            svc = self.osProcessClasses._getOb(id)
            svc.setZenProperty("zMonitor", monitor)
        if REQUEST: return self()


    security.declareProtected(ZEN_MANAGE_DMD, 'removeOSProcessClasses')
    def removeOSProcessClasses(self, ids=None, REQUEST=None):
        """Remove OSProcessClasses from an EventClass.
        """
        if not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        for id in ids:
            # delete related os process instances
            klass = self.osProcessClasses._getOb(id)
            for p in klass.instances():
                p.device().os.processes._delObject(p.id)
            self.osProcessClasses._delObject(id)
        self.manage_resequenceProcesses()
        if REQUEST: return self()


    security.declareProtected(ZEN_MANAGE_DMD, 'moveOSProcessClasses')
    def moveOSProcessClasses(self, moveTarget, ids=None, REQUEST=None):
        """Move OSProcessClasses from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.osProcessClasses._getOb(id)
            rec._operation = 1 # moving object state
            self.osProcessClasses._delObject(id)
            target.osProcessClasses._setObject(id, rec)            
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def buildZProperties(self):
        if hasattr(aq_base(self), "zCountProcs"): return
        self._setProperty("zCountProcs", False, type="boolean")
        self._setProperty("zAlertOnRestart", False, type="boolean")
        self._setProperty("zMonitor", True, type="boolean")
        self._setProperty("zFailSeverity", 4, type="int")
        self._setProperty("zModelerLock", UNLOCKED, type="int")
        self._setProperty("zSendEventWhenBlockedFlag", False, type="boolean")

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        targets = []
        for osc in self.osProcessClasses():
            targets += osc.getUserCommandTargets()
        for org in self.children():
            targets += org.getUserCommandTargets()
        return targets


    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/osProcessOrganizerManage'


InitializeClass(OSProcessOrganizer)
