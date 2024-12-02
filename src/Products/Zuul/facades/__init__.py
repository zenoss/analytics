##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
Zuul facades are part of the Python API.  The main functions of facades are
(1) given a unique identified (UID) retrieve a ZenModel object and return info
objects representing objects related to the retrieved object, and (2) given an
info object bind its properties to a ZenModel object and save it. The UID is
typically an acquisition path, e.g. '/zport/dmd/Devices'. Facades use an
IModelCatalogTool to search for the ZenModel object using the UID.

Documentation for the classes and methods in this module can be found in the
definition of the interface that they implement.
"""

import logging
import re
from itertools import imap, islice
from Acquisition import aq_parent
from zope.event import notify
from OFS.ObjectManager import checkValidId
from zope.interface import implements
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.ComponentOrganizer import ComponentOrganizer
from Products.AdvancedQuery import MatchRegexp, And, Or, Eq, Between, In, MatchGlob
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.Zuul.interfaces import IFacade, ITreeNode
from Products.Zuul.interfaces import (
    ITreeFacade, IInfo, IOrganizerInfo
)
from Products.Zuul.utils import unbrain, get_dmd, UncataloguedObjectException
from Products.Zuul.tree import SearchResults, StaleResultsException
from Products.ZenUtils.IpUtil import numbip, checkip, IpAddressError, ensureIp
from Products.ZenUtils.IpUtil import getSubnetBounds
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul import getFacade
from Products.Zuul.catalog.interfaces import IModelCatalogTool

log = logging.getLogger('zen.Zuul')

organizersToClass = {
    "groups": "DeviceGroup",
    "systems": "System",
    "location": "Location"
}
organizersToPath = {
    "groups": "Groups",
    "systems": "Systems",
    "location": "Locations"

}

class ObjectNotFoundException(Exception):
    pass


class ZuulFacade(object):
    implements(IFacade)

    def __init__(self, context):
        self.context = context

    @property
    def _dmd(self):
        """
        A way for facades to access the data layer
        """
        try:
            return self.context.dmd.primaryAq()
        except Exception:
            return get_dmd()

    def _getObject(self, uid):
        try:
            obj = self._dmd.unrestrictedTraverse(str(uid))
        except Exception as e:
            args = (uid, e.__class__.__name__, e)
            raise ObjectNotFoundException('Cannot find "%s". %s: %s' % args)
        return obj

    def getInfo(self, uid=None):
        obj = self._getObject(uid)
        return IInfo(obj)

    def setInfo(self, uid, data):
        """
        Given a dictionary of {property name: property value}
        this will populate the datapoint
        @param uid unique identifier of the object we are editing
        @type uid string
        @param data properties to update
        @type data Dictionary
        @return IInfo with the updated properties
        """
        info = self.getInfo(uid)

        # see if we need to rename the object
        newId = None
        if 'newId' in data:
            newId = data['newId']
            del data['newId']
            info.rename(newId)

        for key in data.keys():
            if hasattr(info, key):
                setattr(info, key, data[key])
        return info

    def deleteObject(self, uid):
        obj = self._getObject(uid)
        context = aq_parent(obj)
        context._delObject(obj.id)


class TreeFacade(ZuulFacade):
    implements(ITreeFacade)

    def getTree(self, uid=None):
        obj = self._getObject(uid)
        try:
            return ITreeNode(obj)
        except UncataloguedObjectException:
            pass

    def _getObject(self, uid=None):
        if not uid:
            return self._root
        return super(TreeFacade, self)._getObject(uid)

    def _root(self):
        raise NotImplementedError

    def deviceCount(self, uid=None):
        cat = IModelCatalogTool(self._getObject(uid))
        return cat.count('Products.ZenModel.Device.Device')

    def validRegex(self, r):
        try:
            re.compile(r)
            return True
        except Exception:
            return False

    def findMatchingOrganizers(self, organizerClass, organizerPath, userFilter):
        filterRegex = '(?i)^%s.*%s.*' % (organizerPath, userFilter)
        filterRegex = '/zport/dmd/{0}*{1}*'.format(organizerPath, userFilter)
        if self.validRegex(filterRegex):
            orgquery = (Eq('objectImplements','Products.ZenModel.%s.%s' % (organizerClass, organizerClass)) &
                        MatchRegexp('uid', filterRegex))
            paths = [ "{0}".format(b.getPath()) for b in IModelCatalogTool(self._dmd).search(query=orgquery)]
            if paths:
                return In('path', paths)

    def getDeviceBrains(self, uid=None, start=0, limit=50, sort='name',
                        dir='ASC', params=None, hashcheck=None):
        return self.getObjectBrains(uid=uid, start=start, limit=limit, sort=sort,
                                    dir=dir, params=params, hashcheck=hashcheck, types='Products.ZenModel.Device.Device')

    def getObjectBrains(self, uid=None, start=0, limit=50, sort='name',
                        dir='ASC', params=None, hashcheck=None, types=(), fields=[]):

        cat = IModelCatalogTool(self._getObject(uid))

        reverse = bool(dir == 'DESC')
        qs = []
        query = None
        globFilters = {}
        prodStates = None
        params = params if params else {}
        for key, value in params.iteritems():
            if key == 'ipAddress':
                qs.append(MatchGlob('text_ipAddress', '{}*'.format(value)))
            elif key == 'productionState':
                qs.append(Or(*[Eq('productionState', str(state))
                             for state in value]))
            # ZEN-30966 - stringify values from the 'priority' list if it's passed in for query criteria
            elif key == 'priority':
                qs.append(Or(*[Eq('priority', str(priority))
                               for priority in value]))
            # ZEN-10057 - move filtering on indexed groups/systems/location from post-filter to query
            elif key in organizersToClass:
                organizerQuery = self.findMatchingOrganizers(organizersToClass[key], organizersToPath[key], value)
                if not organizerQuery:
                    return []
                qs.append(organizerQuery)
            else:
                globFilters[key] = value
        if qs:
            query = And(*qs)

        return cat.search(
                types, start=start,
                limit=limit, orderby=sort, reverse=reverse,
                query=query, globFilters=globFilters, hashcheck=hashcheck, fields=fields)


    def getDevices(self, uid=None, start=0, limit=50, sort='name', dir='ASC',
                   params=None, hashcheck=None):
        params = params if params else {}
        # Passing a key that's not an index in the catalog will
        # cause a serious performance penalty.  Remove 'status' from
        # the 'params' parameter before passing it on.
        statuses = params.pop('status', None)
        brains = self.getDeviceBrains(uid, start, limit, sort, dir, params,
                                      hashcheck)

        # ZEN-10057 - Handle the case of empty results for a filter with no matches
        if not brains:
            return SearchResults(iter([]), 0, '0')

        devices = [ IInfo(obj) for obj in imap(unbrain, brains) if obj ]

        if statuses is not None and len(statuses) < 3:
            devices = [d for d in devices if d.status in statuses]

        uuids = set(dev.uuid for dev in devices)
        if uuids:
            zep = getFacade('zep', self._dmd)
            severities = zep.getEventSeverities(uuids)
            for device in devices:
                device.setEventSeverities(severities[device.uuid])

        return SearchResults(iter(devices), brains.total, brains.hash_)

    def getInstances(self, uid=None, start=0, limit=50, sort='name',
                     dir='ASC', params=None):
        # do the catalog search
        cat = IModelCatalogTool(self._getObject(uid))
        reverse = bool(dir == 'DESC')
        brains = cat.search(self._instanceClass, start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        objs = imap(unbrain, brains)

        # convert to info objects
        return SearchResults(imap(IInfo, objs), brains.total, brains.hash_)

    def addOrganizer(self, contextUid, id, description=''):
        context = self._getObject(contextUid)
        context.manage_addOrganizer(id)
        if id.startswith("/"):
            organizer = context.getOrganizer(id)
        else:
            # call prepId for each segment.
            id = '/'.join(context.prepId(s) for s in id.split('/'))
            organizer = context._getOb(id)
        organizer.description = description
        return IOrganizerInfo(organizer)

    def addClass(self, contextUid, id):
        context = self._getObject(contextUid)
        _class = self._classFactory(contextUid)(id)
        relationship = getattr(context, self._classRelationship)
        checkValidId(relationship, id)
        relationship._setObject(id, _class)
        return '%s/%s/%s' % (contextUid, self._classRelationship, id)

    def deleteNode(self, uid):
        self.deleteObject(uid)

    def moveOrganizer(self, targetUid, organizerUid):
        """
        Will move the organizerUid to be underneath the targetUid.

        @param string targetUid: unique id of where we want
        to move the organizer
        @param string organizerUid: unique id of the ogranizer we are moving
        """
        organizer = self._getObject(organizerUid)
        parent = organizer.getPrimaryParent()
        parent.moveOrganizer(targetUid, [organizer.id])
        target = self._getObject(targetUid)
        # Get a list of the organizer's child objects to reindex
        childObjects = []
        if isinstance(organizer, DeviceOrganizer):
            childObjects = organizer.getSubDevices()
        elif isinstance(organizer, ComponentOrganizer):
            childObjects = organizer.getSubComponents()

        for dev in childObjects:
            dev.index_object()
            notify(IndexingEvent(dev, 'path'))
        return IOrganizerInfo(target._getOb(organizer.id))


from .networkfacade import NetworkFacade, Network6Facade
from .processfacade import ProcessFacade
from .servicefacade import ServiceFacade
from .devicefacade import DeviceFacade
from .devicedumpload import DeviceDumpLoadFacade
from .propertiesfacade import PropertiesFacade
from .devicemanagementfacade import DeviceManagementFacade
from .templatefacade import TemplateFacade
from .zenpackfacade import ZenPackFacade
from .mibfacade import MibFacade
from .triggersfacade import TriggersFacade
from .zepfacade import ZepFacade
from .reportfacade import ReportFacade
from .jobsfacade import JobsFacade
from .eventclassesfacade import EventClassesFacade
from .manufacturersfacade import ManufacturersFacade
from .metricfacade import MetricFacade
from .application import ApplicationFacade
from .monitor import MonitorFacade
from userfacade import UserFacade
from .hostfacade import HostFacade
from .modelqueryfacade import ModelQueryFacade
