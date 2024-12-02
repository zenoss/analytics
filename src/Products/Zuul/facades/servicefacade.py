##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import logging
import re
from zope.interface import implements
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.IpServiceClass import IpServiceClass
from Products.ZenModel.WinServiceClass import WinServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.Zuul.facades import TreeFacade
from Products.Zuul.utils import unbrain, UncataloguedObjectException
from Products.Zuul.utils import safe_hasattr
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IInfo, ITreeFacade, IServiceFacade
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.infos.service import ServiceOrganizerNode
from Acquisition import aq_base, aq_parent


log = logging.getLogger('zen.ServiceFacade')

class ServiceFacade(TreeFacade):
    implements(IServiceFacade, ITreeFacade)

    def _classFactory(self, contextUid):
        if contextUid.startswith("/zport/dmd/Services/IpService"):
            classFactory = IpServiceClass
        elif contextUid.startswith("/zport/dmd/Services/WinService"):
            classFactory = WinServiceClass
        else:
            raise Exception("Invalid service context UID: " + contextUid)
        return classFactory

    @property
    def _classRelationship(self):
        return 'serviceclasses'

    @property
    def _root(self):
        return self._dmd.Services

    @property
    def _instanceClass(self):
        return "Products.ZenModel.Service.Service"

    def _getSecondaryParent(self, obj):
        return obj.serviceclass()

    def getOrganizerTree(self, id):
        obj = self._getObject(id)
        try:
            return ServiceOrganizerNode(obj)
        except UncataloguedObjectException:
            pass

    def getParentInfo(self, uid=None):
        obj = self._getObject(uid)
        if isinstance(obj, ServiceClass):
            parent = aq_base(obj.serviceorganizer())
        elif isinstance(obj, ServiceOrganizer):
            parent = aq_base(obj.getParentNode())
        else:
            raise Exception('Illegal type %s' % obj.__class__.__name__)

        info = IInfo(parent)
        return info

    def _serviceSearch(self, limit=None, start=None, sort='name', dir='ASC',
              params=None, uid=None, criteria=(), fields=None):
        cat = IModelCatalogTool(self._getObject(uid))
        reverse = dir=='DESC'
        query = {}
        if params:
            for param in [ 'name', 'port' ]:
                if params.get(param):
                    query[param] = "*{0}*".format(params.get(param))

        return cat.search("Products.ZenModel.ServiceClass.ServiceClass",
                          start=start, limit=limit, orderby=sort,
                          reverse=reverse, query=query, fields=fields)

    def getClassNames(self, uid=None, query=None):
        params = None
        if query:
            params = {'name':query}
        data = []
        brains = self._serviceSearch(uid=uid, params=params, fields=["uid", "name"])
        for klass in brains:
            value = klass.getPath().lstrip('/zport/dmd/Services')
            path = re.sub(r'/serviceclasses/.*', r'/', value)+klass.name
            data.append({'value':value, 'name':klass.name, 'path':path}) 
        return data

    @info
    def getList(self, limit=None, start=None, sort='name', dir='DESC',
              params=None, uid=None, criteria=()):
        searchResults = self._serviceSearch(limit, start, sort, dir, params, uid, criteria)
        if searchResults.areBrains:
            serviceClasses = [unbrain(brain) for brain in searchResults]
        else:
            serviceClasses = searchResults

        # the info decorator changes the returned serviceClasses to serviceInfos
        return {'serviceInfos': serviceClasses,
                'total': searchResults.total,
                'hash': searchResults.hash_,
                }

    def moveServices(self, sourceUids, targetUid):
        moveTarget = targetUid.replace('/zport/dmd/Services/', '')

        for sourceUid in sourceUids:
            sourceObj = self._getObject(sourceUid)

            if isinstance(sourceObj, ServiceOrganizer):
                sourceParent = aq_parent(sourceObj)
                sourceParent.moveOrganizer( moveTarget, (sourceObj.id,) )
                targetServiceOrganizer = getattr(sourceParent.getDmdRoot(sourceParent.dmdRootName).getOrganizer(moveTarget), sourceObj.id) 
                for serviceClass in targetServiceOrganizer.serviceclasses(): 
                    serviceClass.updateServicesInGlobalCatalog() 

            elif isinstance(sourceObj, ServiceClass):
                sourceParent = sourceObj.serviceorganizer()
                sourceParent.moveServiceClasses( moveTarget, (sourceObj.id,) )
                getattr(sourceParent.getChildMoveTarget(moveTarget).serviceclasses, sourceObj.id).updateServicesInGlobalCatalog()

            else:
                args = (sourceUid, sourceObj.__class__.__name__)
                raise Exception('Cannot move service %s of type %s' % args)

    def getUnmonitoredStartModes(self, uid):
        monitoredStartModes = [x[0] for x in self.getMonitoredStartModes(uid)]
        for startMode in ['Auto', 'Manual', 'Disabled', 'Not Installed']:
            if startMode not in monitoredStartModes:
                yield [startMode]

    def getMonitoredStartModes(self, uid):
        ob = self._getObject(uid)
        if safe_hasattr(ob, 'monitoredStartModes'):
            for startMode in ob.monitoredStartModes:
                yield [startMode]
    
