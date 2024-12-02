##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
log = logging.getLogger("zen.ServiceOrganizer")

from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Products.ZenModel.ZenossSecurity import *
from Acquisition import aq_base
from Commandable import Commandable
from ZenPackable import ZenPackable

from Products.ZenRelations.RelSchema import *
from Products.ZenRelations.ZenPropertyManager import iszprop


from Organizer import Organizer
from ServiceClass import ServiceClass
from IpServiceClass import IpServiceClass

def manage_addServiceOrganizer(context, id, REQUEST = None):
    """make a device class"""
    sc = ServiceOrganizer(id)
    context._setObject(id, sc)
    sc = context._getOb(id)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

addServiceOrganizer = DTMLFile('dtml/addServiceOrganizer',globals())

class ServiceOrganizer(Organizer, Commandable, ZenPackable):
    meta_type = "ServiceOrganizer"
    dmdRootName = "Services"
    default_catalog = "serviceSearch"

    description = ""

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations = Organizer._relations + ZenPackable._relations + (
        ("serviceclasses", ToManyCont(ToOne,"Products.ZenModel.ServiceClass","serviceorganizer")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        )

    factory_type_information = (
        {
            'id'             : 'ServiceOrganizer',
            'meta_type'      : 'ServiceOrganizer',
            'icon'           : 'ServiceOrganizer.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServiceOrganizer',
            'immediate_view' : 'serviceOrganizerOverview',
            'actions'        :
            (
                { 'id'            : 'classes'
                , 'name'          : 'Classes'
                , 'action'        : 'serviceOrganizerOverview'
                , 'permissions'   : (
                  Permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'serviceOrganizerManage'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'zproperties'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def __init__(self, id=None, description=None):
        if not id: id = self.dmdRootName
        super(ServiceOrganizer, self).__init__(id, description)
        if self.id == self.dmdRootName:
            self.createCatalog()
            self.buildZProperties()


    def find(self, query):
        """Find a service class by is serviceKey.
        """
        cat = getattr(self, self.default_catalog, None)
        if not cat: return
        brains = cat({'serviceKeys': query})
        if not brains: return None
        for brain in brains:
            if brain.getPrimaryId.startswith(self.getPrimaryId()):
                try:
                    return self.getObjByPath(brain.getPrimaryId)
                except KeyError:
                    log.warn("bad path '%s' for index '%s'",
                        brain.getPrimaryId, self.default_catalog)


    def checkValidId(self, id):
        """Checks a valid id
        """
        relationship = getattr(self, 'serviceclasses')
        try:
            relationship.checkValidId(id)
            return True
        except Exception as e:
            return str(e)


    def getSubClassesGen(self):
        """Return generator that goes through all process classes.
        """
        for proc in self.serviceclasses.objectValuesGen():
            yield proc
        for subgroup in self.children():
            for proc in subgroup.getSubClassesGen():
                yield proc


    def getSubClassesSorted(self):
        '''Return list of the process classes sorted by sequence.
        '''
        procs = sorted(self.getSubClassesGen(),
                    key=lambda a: a.sequence)
        # reset sequence numbers to 0-n
        for i, p in enumerate(procs):
            p.sequence = i
        return procs


    def countClasses(self):
        """Count all serviceclasses with in a ServiceOrganizer.
        """
        count = self.serviceclasses.countObjects()
        for group in self.children():
            count += group.countClasses()
        return count


    def createServiceClass(self, name="", description="",
                           path="", factory=ServiceClass, **kwargs):
        """Create a service class (or retrun existing) based on keywords.
        """
        svcs = self.getDmdRoot(self.dmdRootName)
        svcorg = svcs.createOrganizer(path)
        svccl = svcorg.find(name)
        if not svccl:
            svccl = factory(name, (name,),description=description, **kwargs)
            svcorg.serviceclasses._setObject(svccl.id, svccl)
            svccl = svcorg.serviceclasses._getOb(svccl.id)
        return svccl

    def saveZenProperties(self, pfilt=iszprop, REQUEST=None):
        """
        Save all ZenProperties found in the REQUEST.form object.
        Overridden so that service instances can be re-indexed if needed
        """
        #get value to see if it changes
        monitor = self.zMonitor
        result = super(ServiceOrganizer, self).saveZenProperties( pfilt, REQUEST)

        if monitor != self.zMonitor :
            #indexes need to be updated so that the updated config will be sent
            #can be slow if done at /Services would be nice to run asynch
            self._indexServiceClassInstances()
        return result

    def deleteZenProperty(self, propname=None, REQUEST=None):
        """
        Delete device tree properties from the this DeviceClass object.
        Overridden to intercept zMonitor changes
        """
        monitor = self.zMonitor
        result = super(ServiceOrganizer, self).deleteZenProperty( propname, REQUEST)
        if monitor != self.zMonitor :
            #indexes need to be updated so that the updated config will be sent
            #can be slow if done at /Services would be nice to run asynch
            self._indexServiceClassInstances()

        return result

    def _indexServiceClassInstances(self):
        """
        indexes any service class instances in the hierarchy
        """
        organizers = [self]
        while organizers:
            for org in organizers:
                for sc in org.serviceclasses():
                    sc._indexInstances()

            oldOrgs = organizers
            organizers = []
            for org in oldOrgs:
                organizers.extend(org.children())


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addServiceClass')
    def manage_addServiceClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = ServiceClass(id)
            self.serviceclasses._setObject(id, sc)
        if REQUEST or not id:
            return self.callZenScreen(REQUEST)
        else:
            return self.serviceclasses._getOb(id)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addIpServiceClass')
    def manage_addIpServiceClass(self, id=None, REQUEST=None):
        """Create a new service class in this Organizer.
        """
        if id:
            sc = IpServiceClass(id)
            self.serviceclasses._setObject(id, sc)
        if REQUEST or not id:
            return self.callZenScreen(REQUEST)
        else:
            return self.serviceclasses._getOb(id)


    def unmonitorServiceClasses(self, ids=None, REQUEST=None):
        return self.monitorServiceClasses(ids, False, REQUEST)


    def monitorServiceClasses(self, ids=None, monitor=True, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        for id in ids:
            svc = self.serviceclasses._getOb(id)
            svc.setZenProperty("zMonitor", monitor)
            svc._indexServiceClassInstances()
        if REQUEST: return self()


    def removeServiceClasses(self, ids=None, REQUEST=None):
        """Remove ServiceClasses from an EventClass.
        """
        if not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        for id in ids:
            self.serviceclasses._delObject(id)
        if REQUEST: return self()


    def moveServiceClasses(self, moveTarget, ids=None, REQUEST=None):
        """Move ServiceClasses from this EventClass to moveTarget.
        """
        if not moveTarget or not ids: return self()
        if isinstance(ids, basestring): ids = (ids,)
        target = self.getChildMoveTarget(moveTarget)
        for id in ids:
            rec = self.serviceclasses._getOb(id)
            rec._operation = 1 # moving object state
            self.serviceclasses._delObject(id)
            target.serviceclasses._setObject(id, rec)
            svc = target.serviceclasses._getOb(id)
            svc._indexInstances()
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())


    def buildZProperties(self):
        if hasattr(aq_base(self), "zMonitor"): return
        self._setProperty("zMonitor", False, type="boolean")
        self._setProperty("zFailSeverity", 5, type="int")
        self._setProperty("zHideFieldsFromList", [], type="lines")


    security.declareProtected(ZEN_MANAGE_DMD, 'reIndex')
    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        for srv in self.getSubOrganizers():
            for inst in srv.serviceclasses():
                inst.index_object()


    security.declareProtected(ZEN_ADD, 'createCatalog')
    def createCatalog(self):
        """Create a catalog for ServiceClass searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        manage_addZCatalog(self, self.default_catalog,
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        zcat.addIndex('serviceKeys', 'KeywordIndex')
        zcat.addColumn('getPrimaryId')


    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        targets = []
        for sc in self.serviceclasses():
            targets += sc.getUserCommandTargets()
        for so in self.children():
            targets += so.getUserCommandTargets()
        return targets


    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/serviceOrganizerManage'


    def parseServiceLiveSearchString(self, iddescstr):
        """ Parse a string of id and description from a live search
        """
        id = iddescstr.split(None, 1)[0]
        return id


InitializeClass(ServiceOrganizer)
