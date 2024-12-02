##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re
import socket

from collections import OrderedDict
from itertools import imap

import six

from AccessControl import getSecurityManager
from Acquisition import aq_base
from Products.AdvancedQuery import Eq, Or, Generic, And, MatchGlob
from ZODB.transact import transact
from zope.component import getMultiAdapter
from zope.event import notify
from zope.interface import implements

from Products.DataCollector.Plugins import (
    CoreImporter,
    loadPlugins,
    PackImporter,
)
from Products.Jobber.jobs import FacadeMethodJob
from Products.ZenCollector.configcache.api import ConfigCache
from Products.ZenEvents.Event import Event
from Products.ZenMessaging.ChangeEvents.events import (
    ObjectAddedToOrganizerEvent,
    ObjectRemovedFromOrganizerEvent,
)
from Products.ZenModel.ComponentGroup import ComponentGroup
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.Device import Device
from Products.ZenModel.Location import Location
from Products.ZenModel.System import System
from Products.ZenModel.ZenossSecurity import ZEN_VIEW
from Products.ZenUtils.IpUtil import isip, getHostByName
from Products.ZenUtils.Utils import getObjectsFromCatalog

from Products.Zuul.catalog.component_catalog import (
    get_component_field_spec,
    pad_numeric_values_for_indexing,
)
from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.decorators import info
from Products.Zuul.exceptions import DatapointNameConfict
from Products.Zuul.facades import TreeFacade
from Products.Zuul import getFacade
from Products.Zuul.infos.metricserver import (
    MultiContextMetricServiceGraphDefinition,
)
from Products.Zuul.interfaces import IDeviceCollectorChangeEvent
from Products.Zuul.interfaces import (
    IDeviceFacade,
    IInfo,
    ITemplateNode,
    IMetricServiceGraphDefinition,
)
from Products.Zuul.tree import SearchResults
from Products.Zuul.utils import unbrain
from Products.Zuul.utils import (
    UncataloguedObjectException,
    ZuulMessageFactory as _t,
)

iszprop = re.compile("z[A-Z]").match
log = logging.getLogger("zen.DeviceFacade")


class DeviceCollectorChangeEvent(object):
    implements(IDeviceCollectorChangeEvent)
    """
    Collector change event for device.
    """

    def __init__(self, context, collector, movedDevices, asynchronous):
        self._context = context
        self._collector = collector
        self._movedDevices = movedDevices
        self._asynchronous = asynchronous
        self.jobs = []

    @property
    def context(self):
        return self._context

    @property
    def collector(self):
        return self._collector

    @property
    def movedDevices(self):
        return self._movedDevices

    @property
    def asynchronous(self):
        return self._asynchronous


class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """

    implements(IDeviceFacade)

    def _classFactory(self, contextUid):
        return DeviceClass

    @property
    def _root(self):
        return self._dmd.Devices

    @property
    def _instanceClass(self):
        return "Products.ZenModel.Device.Device"

    def setInfo(self, uid, data):
        """ """
        super(DeviceFacade, self).setInfo(uid, data)
        obj = self._getObject(uid)
        if isinstance(obj, Device):
            obj.index_object()
        notify(IndexingEvent(obj))

    def findComponentIndex(
        self,
        componentUid,
        uid=None,
        meta_type=None,
        sort="name",
        dir="ASC",
        name=None,
    ):
        brains, total = self._typecatComponentBrains(
            uid=uid, meta_type=meta_type, sort=sort, dir=dir, name=name
        )
        if brains is None:
            comps = self._componentSearch(
                uid=uid, meta_type=meta_type, sort=sort, dir=dir, name=name
            )
            for i, b in enumerate(comps):
                if "/".join(b._object.getPrimaryPath()) == componentUid:
                    return i
        else:
            for i, b in enumerate(brains):
                if b.getPath() == componentUid:
                    return i

    def _filterComponents(self, comps, keys, query):
        """
        Returns a list of components where one of the attributes in keys
        contains the query (case-insensitive).

        @type  comps: SearchResults
        @param comps: All the Components for this query
        @type  keys: List
        @param keys: List of strings of fields that we are filtering on
        @type  query: String
        @param query: Search Term
        @rtype:   List
        @return:  List of Component Info objects that match the query
        """
        results = []
        query = query.lower()
        for comp in comps:
            keep = False
            for key in keys:
                # non searchable fields
                if key in ("uid", "uuid", "events", "status", "severity"):
                    continue
                val = getattr(comp, key, None)
                if not val:
                    continue
                if callable(val):
                    val = val()
                if IInfo.providedBy(val):
                    val = val.name
                if query in str(val).lower():
                    keep = True
                    break
            if keep:
                results.append(comp)
        return results

    def _typecatComponentBrains(
        self,
        uid=None,
        types=(),
        meta_type=(),
        start=0,
        limit=None,
        sort="name",
        dir="ASC",
        name=None,
        keys=(),
    ):
        obj = self._getObject(uid)
        spec = get_component_field_spec(meta_type)
        if spec is None:
            return None, 0
        typecat = spec.get_catalog(obj, meta_type)
        sortspec = ()
        if sort:
            if sort not in typecat._catalog.indexes:
                # Fall back to slow queries and sorting
                return None, 0
            sortspec = ((sort, dir),)
        querySet = [Generic("path", uid)]
        if name:
            querySet.append(
                Or(*(MatchGlob(field, "*%s*" % name) for field in spec.fields))
            )
        brains = typecat.evalAdvancedQuery(And(*querySet), sortspec)
        total = len(brains)
        if limit is None:
            brains = brains[start:]
        else:
            brains = brains[start : start + limit]
        return brains, total

    def _typecatComponentPostProcess(
        self, brains, total, sort="name", reverse=False
    ):
        hash_ = str(total)
        comps = map(IInfo, map(unbrain, brains))
        # fetch any rrd data necessary
        self.bulkLoadMetricData(comps)
        # Do one big lookup of component events and add to the result objects
        showSeverityIcon = (
            self.context.dmd.UserInterfaceSettings.getInterfaceSettings().get(
                "showEventSeverityIcons"
            )
        )
        if showSeverityIcon:
            uuids = [r.uuid for r in comps]
            zep = getFacade("zep")
            severities = zep.getWorstSeverity(uuids)
            for r in comps:
                r.setWorstEventSeverity(severities[r.uuid])
        sortedComps = sorted(
            comps, key=lambda x: getattr(x, sort), reverse=reverse
        )
        return SearchResults(iter(sortedComps), total, hash_, False)

    # Get components from model catalog. Not used for now
    def _get_component_brains_from_model_catalog(self, uid, meta_type=()):
        """ """
        model_catalog = IModelCatalogTool(self.context.dmd)
        query = {}
        if meta_type:
            query["meta_type"] = meta_type
        query["objectImplements"] = (
            "Products.ZenModel.DeviceComponent.DeviceComponent"
        )
        query["deviceId"] = uid
        model_query_results = model_catalog.search(query=query)
        brains = list(model_query_results.results)
        return brains

    def _componentSearch(
        self,
        uid=None,
        types=(),
        meta_type=(),
        start=0,
        limit=None,
        sort="name",
        dir="ASC",
        name=None,
        keys=(),
    ):
        reverse = dir == "DESC"
        if (
            isinstance(meta_type, six.string_types)
            and get_component_field_spec(meta_type) is not None
        ):
            brains, total = self._typecatComponentBrains(
                uid, types, meta_type, start, limit, sort, dir, name, keys
            )
            if brains is not None:
                return self._typecatComponentPostProcess(
                    brains, total, sort, reverse
                )
        if isinstance(meta_type, six.string_types):
            meta_type = (meta_type,)
        if isinstance(types, six.string_types):
            types = (types,)
        querySet = []
        if meta_type:
            querySet.append(Or(*(Eq("meta_type", t) for t in meta_type)))
        querySet.append(Generic("getAllPaths", uid))
        query = And(*querySet)
        obj = self._getObject(uid)

        cat = obj.device().componentSearch
        if "getAllPaths" not in cat.indexes():
            obj.device()._createComponentSearchPathIndex()
        brains = cat.evalAdvancedQuery(query)

        # unbrain the results
        comps = []
        for brain in brains:
            try:
                comps.append(IInfo(unbrain(brain)))
            except Exception:
                log.warn(
                    'There is broken component "%s" in componentSearch '
                    "catalog on %s device.",
                    brain.id,
                    obj.device().id,
                )

        # filter the components
        if name is not None:
            comps = self._filterComponents(comps, keys, name)

        total = len(comps)
        hash_ = str(total)

        def componentSortKey(parent):
            val = getattr(parent, sort)
            if val:
                if isinstance(val, list):
                    val = val[0]
                if callable(val):
                    val = val()
                if IInfo.providedBy(val):
                    val = val.name
            return pad_numeric_values_for_indexing(val)

        # sort the components
        sortedResults = sorted(comps, key=componentSortKey, reverse=reverse)

        # limit the search results to the specified range
        if limit is None:
            pagedResult = sortedResults[start:]
        else:
            pagedResult = sortedResults[start : start + limit]

        # fetch any rrd data necessary
        self.bulkLoadMetricData(pagedResult)

        # Do one big lookup of component events and add to the result objects
        showSeverityIcon = (
            self.context.dmd.UserInterfaceSettings.getInterfaceSettings().get(
                "showEventSeverityIcons"
            )
        )
        if showSeverityIcon:
            uuids = [r.uuid for r in pagedResult]
            zep = getFacade("zep")
            severities = zep.getWorstSeverity(uuids)
            for r in pagedResult:
                r.setWorstEventSeverity(severities[r.uuid])

        return SearchResults(iter(pagedResult), total, hash_, False)

    def getComponents(
        self,
        uid=None,
        types=(),
        meta_type=(),
        start=0,
        limit=None,
        sort="name",
        dir="ASC",
        name=None,
        keys=(),
    ):
        return self._componentSearch(
            uid,
            types,
            meta_type,
            start,
            limit,
            sort,
            dir,
            name=name,
            keys=keys,
        )

    def bulkLoadMetricData(self, infos):
        """
        If the info objects have the attribute dataPointsToFetch we
        will load all the datapoints in one metric service query
        instead of one per info object
        """
        if len(infos) == 0:
            return
        datapoints = set()
        indexedInfos = {}
        for inf in infos:
            indexedInfos[inf._object.getResourceKey()] = inf
            if hasattr(inf, "dataPointsToFetch"):
                [datapoints.add(dp) for dp in inf.dataPointsToFetch]

        # in case no metrics were asked for
        if len(datapoints) == 0:
            return
        # get the metric facade
        mfacade = getFacade("metric", self._dmd)
        # metric facade expects zenmodel objects or uids
        results = mfacade.getMultiValues(
            [i._object for i in infos], datapoints, returnSet="LAST"
        )

        # assign the metrics to the info objects
        for resourceKey, record in results.iteritems():
            if indexedInfos.get(resourceKey) is not None:
                info = indexedInfos[resourceKey]
                for key, val in record.iteritems():
                    info.setBulkLoadProperty(key, val)

    # Get component types from model catalog. Not used for now
    def _get_component_types_from_model_catalog(self, uid):
        """ """
        componentTypes = {}
        uuidMap = {}
        model_catalog = IModelCatalogTool(self.context.dmd)
        model_query = Eq(
            "objectImplements",
            "Products.ZenModel.DeviceComponent.DeviceComponent",
        )
        model_query = And(model_query, Eq("deviceId", uid))
        model_query_results = model_catalog.search(
            query=model_query, fields=["uuid", "meta_type"]
        )

        for brain in model_query_results.results:
            uuidMap[brain.uuid] = brain.meta_type
            compType = componentTypes.setdefault(
                brain.meta_type, {"count": 0, "severity": 0}
            )
            compType["count"] += 1
        return (componentTypes, uuidMap)

    def _get_component_types_from_zcatalog(self, uid):
        """ """
        componentTypes = {}
        uuidMap = {}
        dev = self._getObject(uid)
        for brain in dev.componentSearch():
            uuidMap[brain.getUUID] = brain.meta_type
            compType = componentTypes.setdefault(
                brain.meta_type, {"count": 0, "severity": 0}
            )
            compType["count"] += 1
        return (componentTypes, uuidMap)

    def getComponentTree(self, uid):
        from Products.ZenEvents.EventManagerBase import EventManagerBase

        componentTypes, uuidMap = self._get_component_types_from_zcatalog(uid)

        # Do one big lookup of component events and merge back in to type later
        if not uuidMap:
            return []

        zep = getFacade("zep")
        showSeverityIcon = (
            self.context.dmd.UserInterfaceSettings.getInterfaceSettings().get(
                "showEventSeverityIcons"
            )
        )
        if showSeverityIcon:
            severities = zep.getWorstSeverity(uuidMap.keys())
            for uuid, sev in severities.iteritems():
                compType = componentTypes[uuidMap[uuid]]
                compType["severity"] = max(compType["severity"], sev)

        result = []
        for name, compType in componentTypes.iteritems():
            result.append(
                {
                    "type": name,
                    "count": compType["count"],
                    "severity": EventManagerBase.severities.get(
                        compType["severity"], 0
                    ).lower(),
                }
            )

        return result

    def getDeviceUids(self, uid):
        cat = IModelCatalogTool(self._getObject(uid))
        return [
            b.getPath() for b in cat.search("Products.ZenModel.Device.Device")
        ]

    def deleteComponents(self, uids):
        comps = imap(self._getObject, uids)
        for comp in comps:
            if comp.isLockedFromDeletion():
                raise Exception(
                    "Component %s is locked from deletion" % comp.id
                )

            if hasattr(comp, "manage_deleteComponent"):
                comp.manage_deleteComponent()
            else:
                raise Exception(
                    "%s %s cannot be manually deleted"
                    % (getattr(comp, "meta_type", "component"), comp.id)
                )

    def _deleteDevices(self, uids, deleteEvents=False, deletePerf=True):
        @transact
        def dbDeleteDevices(uids):
            devs = imap(self._getObject, uids)
            deletedIds = []
            for dev in devs:
                devid = dev.getId()
                deletedIds.append(devid)
                dev.deleteDevice(
                    deleteStatus=deleteEvents, deletePerf=deletePerf
                )
            return deletedIds

        def uidChunks(uids, chunksize=10):
            i = 0
            maxi = len(uids)
            while i < maxi:
                nexti = i + chunksize
                yield uids[i:nexti]
                i = nexti

        deletedIds = sum(map(dbDeleteDevices, uidChunks(uids)), [])
        for devid in deletedIds:
            self._dmd.ZenEventManager.sendEvent(
                Event(
                    summary="Deleted device: " + devid,
                    severity=2,  # info
                    eventClass="/Change/Remove",  # zEventAction=history
                    device=devid,
                )
            )

    def deleteDevices(self, uids, deleteEvents=False, deletePerf=True):
        """
        Return a list of device uids underneath an organizer. This includes
        all the devices belonging to an child organizers.
        """
        devs = imap(self._getObject, uids)
        for dev in devs:
            if dev.isLockedFromDeletion():
                raise Exception("Device %s is locked from deletion" % dev.id)

        return self._deleteDevices(uids, deleteEvents, deletePerf)

    @info
    def removeDevices(self, uids, organizer):
        # Resolve target if a path
        if isinstance(organizer, six.string_types):
            organizer = self._getObject(organizer)
        devs = map(self._getObject, uids)
        removed = []
        if isinstance(organizer, DeviceGroup):
            for dev in devs:
                oldGroupNames = dev.getDeviceGroupNames()
                newGroupNames = self._removeOrganizer(
                    organizer, list(oldGroupNames)
                )
                if oldGroupNames != newGroupNames:
                    dev.setGroups(newGroupNames)
                    notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                    removed.append(dev)

        elif isinstance(organizer, System):
            for dev in devs:
                oldSystemNames = dev.getSystemNames()
                newSystemNames = self._removeOrganizer(
                    organizer, list(oldSystemNames)
                )
                if newSystemNames != oldSystemNames:
                    dev.setSystems(newSystemNames)
                    notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                    removed.append(dev)

        elif isinstance(organizer, Location):
            for dev in devs:
                dev.setLocation(None)
                notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                removed.append(dev)

        return removed

    def _removeOrganizer(self, organizer, items):
        organizerName = organizer.getOrganizerName()
        if organizerName in items:
            items.remove(organizerName)
        return items

    @info
    def getUserCommands(self, uid=None):
        org = self._getObject(uid)
        return org.getUserCommands()

    def setProductInfo(
        self,
        uid,
        hwManufacturer=None,
        hwProductName=None,
        osManufacturer=None,
        osProductName=None,
    ):
        dev = self._getObject(uid)
        dev.setProductInfo(
            hwManufacturer=hwManufacturer,
            hwProductName=hwProductName,
            osManufacturer=osManufacturer,
            osProductName=osProductName,
        )

    def setProductionState(self, uids, state, asynchronous=False):
        if asynchronous:
            self._dmd.JobManager.addJob(
                FacadeMethodJob,
                description="Set state %s for %s" % (state, ",".join(uids)),
                kwargs={
                    "facadefqdn": (
                        "Products.Zuul.facades.devicefacade.DeviceFacade"
                    ),
                    "method": "_setProductionState",
                    "uids": uids,
                    "state": state,
                },
            )
        else:
            self._setProductionState(uids, state)

    def setLockState(
        self, uids, deletion=False, updates=False, sendEvent=False
    ):
        devs = imap(self._getObject, uids)
        for dev in devs:
            if deletion or updates:
                if deletion:
                    dev.lockFromDeletion(sendEvent)
                if updates:
                    dev.lockFromUpdates(sendEvent)
            else:
                dev.unlock()

    def setMonitor(self, uids, monitor=False):
        comps = imap(self._getObject, uids)
        for comp in comps:
            IInfo(comp).monitor = monitor
            # update the componentSearch catalog
            comp.index_object(idxs=("monitored",))

            # update the global catalog as well
            notify(IndexingEvent(comp, idxs=("monitored",)))

    def pushChanges(self, uids):
        devs = imap(self._getObject, uids)
        if not devs:
            return
        configcache = ConfigCache.new()
        for dev in devs:
            configcache.update_device(dev)

    def modelDevices(self, uids):
        devs = imap(self._getObject, uids)
        for dev in devs:
            dev.collectDevice(background=True)

    def resetCommunityString(self, uid):
        dev = self._getObject(uid)
        dev.manage_snmpCommunity()

    def renameDevice(self, uid, newId, retainGraphData=False):
        dev = self._getObject(uid)
        # pass in the request for the audit
        return dev.renameDevice(newId, self.context.REQUEST, retainGraphData)

    def resumeCollection(self, uid):
        device = self._getObject(uid)
        device.renameInProgress = False
        return "OK!"

    def _moveDevices(self, uids, target):
        # Resolve target if a path
        if isinstance(target, six.string_types):
            target = self._getObject(target)
        devs = (self._getObject(uid) for uid in uids)
        targetname = target.getOrganizerName()
        moved_devices_count = 0
        success = False
        remodel_required = False
        if isinstance(target, DeviceGroup):
            for dev in devs:
                paths = set(dev.getDeviceGroupNames())
                paths.add(targetname)
                dev.setGroups(list(paths))
                notify(ObjectAddedToOrganizerEvent(dev, target))
            success = True
        elif isinstance(target, System):
            for dev in devs:
                paths = set(dev.getSystemNames())
                paths.add(targetname)
                dev.setSystems(list(paths))
                notify(ObjectAddedToOrganizerEvent(dev, target))
            success = True
        elif isinstance(target, Location):
            for dev in devs:
                if dev.location():
                    notify(
                        ObjectRemovedFromOrganizerEvent(dev, dev.location())
                    )
                dev.setLocation(targetname)
                notify(ObjectAddedToOrganizerEvent(dev, target))
            success = True
        elif isinstance(target, DeviceClass):
            moved_devices_count = self._dmd.Devices.moveDevices(
                targetname, [dev.id for dev in devs]
            )
            success = True
            remodel_required = True

        result = {
            "success": success,
            "message": "The %s devices have been moved" % moved_devices_count,
            "remodel_required": remodel_required,
        }
        return result

    def _setProductionState(self, uids, state):
        if isinstance(uids, six.string_types):
            uids = (uids,)
        for uid in uids:
            dev = self._getObject(uid)
            if isinstance(dev, Device):
                dev.setProdState(int(state))

    def doesMoveRequireRemodel(self, uid, target):
        # Resolve target if a path
        if isinstance(target, six.string_types):
            target = self._getObject(target)
        targetClass = target.getPythonDeviceClass()
        dev = self._getObject(uid)
        return dev and dev.__class__ != targetClass

    @info
    def moveDevices(self, uids, target, asynchronous=True):
        if asynchronous:
            devdesc = (
                "device %s" % uids[0].split("/")[-1]
                if len(uids) == 1
                else "%s devices" % len(uids)
            )
            return self._dmd.JobManager.addJob(
                FacadeMethodJob,
                description="Move %s to %s" % (devdesc, target),
                kwargs={
                    "facadefqdn": (
                        "Products.Zuul.facades.devicefacade.DeviceFacade"
                    ),
                    "method": "_moveDevices",
                    "uids": uids,
                    "target": target,
                },
            )
        else:
            return self._moveDevices(uids, target)

    def getDeviceByIpAddress(
        self, deviceName, collector="localhost", ipAddress=""
    ):
        # convert device name to an ip address
        if not ipAddress:
            if isip(deviceName):
                ipAddress = deviceName
            else:
                try:
                    ipAddress = getHostByName(deviceName)
                except socket.error:
                    # look for duplicate name
                    return self.context.Devices.findDeviceByIdExact(deviceName)

        # find a device with the same ip on the same collector
        cat = IModelCatalogTool(self.context.Devices)
        query = And(
            Eq("text_ipAddress", ipAddress),
            Eq("objectImplements", "Products.ZenModel.Device.Device"),
        )
        search_results = cat.search(query=query)

        for brain in search_results.results:
            if brain.getObject().getPerformanceServerName() == collector:
                return brain.getObject()

    def getDeviceByName(self, deviceName):
        return self.context.Devices.findDeviceByIdExact(deviceName)

    @info
    def setCollector(self, uids, collector, moveData=False, asynchronous=True):
        # Keep 'moveData' in signature even though it's unused now
        if asynchronous:
            prettyUids = ", ".join([uid.split("/")[-1] for uid in uids])
            return self._dmd.JobManager.addJob(
                FacadeMethodJob,
                description="Move devices %s to collector %s"
                % (prettyUids, collector),
                kwargs={
                    "facadefqdn": (
                        "Products.Zuul.facades.devicefacade.DeviceFacade"
                    ),
                    "method": "_setCollector",
                    "uids": uids,
                    "collector": collector,
                },
            )
        else:
            return self._setCollector(uids, collector)

    def _setCollector(
        self, uids, collector, moveData=False, asynchronous=True
    ):
        movedDevices = []
        for uid in uids:
            info = self.getInfo(uid)
            movedDevices.append(
                {
                    "id": uid.split("/")[-1],
                    "fromCollector": info.collector,
                }
            )
            info.collector = collector

        # If an event is desired at this point,
        # use a DeviceCollectorChangeEvent here

    @info
    def addDevice(
        self,
        deviceName,
        deviceClass,
        title=None,
        snmpCommunity="",
        snmpPort=161,
        manageIp="",
        model=False,
        collector="localhost",
        rackSlot=0,
        productionState=1000,
        comments="",
        hwManufacturer="",
        hwProductName="",
        osManufacturer="",
        osProductName="",
        priority=3,
        tag="",
        serialNumber="",
        locationPath="",
        zCommandUsername="",
        zCommandPassword="",
        zWinUser="",
        zWinPassword="",
        systemPaths=None,
        groupPaths=None,
        zProperties=None,
        cProperties=None,
    ):
        systemPaths = systemPaths if systemPaths else []
        groupPaths = groupPaths if groupPaths else []
        zProperties = zProperties if zProperties else {}
        cProperties = cProperties if cProperties else {}
        zProps = {
            "zSnmpCommunity": snmpCommunity,
            "zSnmpPort": snmpPort,
            "zCommandUsername": zCommandUsername,
            "zCommandPassword": zCommandPassword,
            "zWinUser": zWinUser,
            "zWinPassword": zWinPassword,
        }
        zProps.update(zProperties)
        model = model and "Auto" or "none"
        perfConf = self._dmd.Monitors.getPerformanceMonitor(collector)
        if perfConf.viewName() != collector:
            raise Exception("Collector `{}` does not exist".format(collector))
        jobrecords = perfConf.addCreateDeviceJob(
            deviceName=deviceName,
            devicePath=deviceClass,
            performanceMonitor=collector,
            discoverProto=model,
            manageIp=manageIp,
            zProperties=zProps,
            cProperties=cProperties,
            rackSlot=rackSlot,
            productionState=productionState,
            comments=comments,
            hwManufacturer=hwManufacturer,
            hwProductName=hwProductName,
            osManufacturer=osManufacturer,
            osProductName=osProductName,
            priority=priority,
            tag=tag,
            serialNumber=serialNumber,
            locationPath=locationPath,
            systemPaths=systemPaths,
            groupPaths=groupPaths,
            title=title,
        )
        return jobrecords

    def remodel(self, deviceUid, collectPlugins="", background=True):
        # fake_request will break not a background command
        fake_request = {"CONTENT_TYPE": "xml"} if background else None
        device = self._getObject(deviceUid)
        return device.getPerformanceServer().collectDevice(
            device,
            background=background,
            collectPlugins=collectPlugins,
            REQUEST=fake_request,
        )

    def addLocalTemplate(self, deviceUid, templateId):
        """
        Adds a local template on the device specified by deviceUid
        @param string deviceUid: absolute path to a device
        @param string templateId: the Id of the new template
        """
        device = self._getObject(deviceUid)
        device.addLocalTemplate(templateId)

    def removeLocalTemplate(self, deviceUid, templateUid):
        """
        Removes a local definition of a template on a device
        @param deviceUid: Absolute path to the device that has the template
        @type deviceUid: str
        @param templateUid: Absolute path to the template we wish to remove
        @type templateUid: str
        """
        device = self._getObject(deviceUid)
        template = self._getObject(templateUid)
        device.removeLocalRRDTemplate(template.id)

    def getTemplates(self, id):
        object = self._getObject(id)

        isDeviceClass = isinstance(object, DeviceClass)
        if isDeviceClass:
            pythonDeviceClass = object.getPythonDeviceClass()

        zDeviceTemplates = object.zDeviceTemplates

        rrdTemplates = object.getRRDTemplates()

        templateNames = []
        boundTemplates = []
        unboundTemplates = []
        for rrdTemplate in rrdTemplates:
            if isDeviceClass and not issubclass(
                pythonDeviceClass, rrdTemplate.getTargetPythonClass()
            ):
                continue
            templateNames.append(rrdTemplate.id)
            if rrdTemplate.id in object.zDeviceTemplates:
                boundTemplates.append(rrdTemplate)
            else:
                unboundTemplates.append(rrdTemplate)

        # used to sort the templates
        def byTitleOrId(obj):
            return obj.titleOrId().lower()

        for rrdTemplate in list(unboundTemplates):
            if rrdTemplate.id.endswith(
                "-replacement"
            ) or rrdTemplate.id.endswith("-addition"):
                if (
                    "-".join(rrdTemplate.id.split("-")[:-1])
                    in zDeviceTemplates
                ):
                    boundTemplates.append(rrdTemplate)
                    unboundTemplates.remove(rrdTemplate)

        def makenode(rrdTemplate, suborg=None):
            uid = "/".join(rrdTemplate.getPrimaryPath())
            path = ""

            # for DeviceClasses show which are bound
            if isinstance(object, DeviceClass):
                if rrdTemplate.id in zDeviceTemplates:
                    path = "%s (%s)" % (path, _t("Bound"))
                if rrdTemplate.id + "-replacement" in templateNames:
                    path = "%s (%s)" % (path, _t("Replaced"))

            # if defined directly on the device do not show the path
            uiPath = rrdTemplate.getUIPath()
            if (not isDeviceClass) and object.titleOrId() in uiPath:
                path = "%s (%s)" % (path, _t("Locally Defined"))
            else:
                path = "%s (%s)" % (path, uiPath)
            return {
                "id": uid,
                "uid": uid,
                "path": path,
                "text": "%s %s" % (rrdTemplate.titleOrId(), path),
                "leaf": True,
            }

        for rrdTemplate in sorted(boundTemplates, key=byTitleOrId):
            yield makenode(rrdTemplate)

        if isDeviceClass:
            available = []
            for rrdTemplate in sorted(unboundTemplates, key=byTitleOrId):
                available.append(makenode(rrdTemplate, "Available"))
            yield {
                "id": "Available",
                "text": "Available",
                "leaf": False,
                "children": available,
            }

    def getLocalTemplates(self, uid):
        """
        Returns a dictionary of every template defined on the device
        specified by the uid.

        @param string uid: absolute path of a device
        @returns [Dict] All the templates defined on this device
        """
        for template in self._getObject(uid).objectValues("RRDTemplate"):
            uid = "/".join(template.getPrimaryPath())
            path = template.getUIPath()
            yield {
                "id": uid,
                "uid": uid,
                "path": path,
                "text": "%s (%s)" % (template.titleOrId(), path),
                "leaf": True,
            }

    def getUnboundTemplates(self, uid):
        return self._getBoundTemplates(uid, False)

    def getBoundTemplates(self, uid):
        return self._getBoundTemplates(uid, True)

    def _getBoundTemplates(self, uid, isBound):
        obj = self._getObject(uid)
        templates = (
            template
            for template in obj.getAvailableTemplates()
            if (template.id in obj.zDeviceTemplates) == isBound
        )
        if isBound:
            templates = sorted(
                templates, key=lambda x: obj.zDeviceTemplates.index(x.id)
            )
        return templates

    def setBoundTemplates(self, uid, templateIds):
        obj = self._getObject(uid)

        # check for datapoint name conflicts
        bound_dp_names = {}
        for template in obj.getAvailableTemplates():
            if template.id in templateIds:
                dp_names = set(template.getRRDDataPointNames())
                intersection = dp_names.intersection(bound_dp_names)
                if intersection:
                    dp_name = intersection.pop()
                    other_id = bound_dp_names[dp_name]
                    raise DatapointNameConfict(
                        "both {template.id} and {other_id} have a "
                        "datapoint named {dp_name}".format(
                            template=template,
                            other_id=other_id,
                            dp_name=dp_name,
                        )
                    )
                for dp_name in dp_names:
                    bound_dp_names[dp_name] = template.id

        obj.bindTemplates(templateIds)

    def resetBoundTemplates(self, uid):
        obj = self._getObject(uid)
        # make sure we have bound templates before we remove them
        if obj.hasProperty("zDeviceTemplates"):
            obj.removeZDeviceTemplates()

    def getOverridableTemplates(self, uid):
        """
        A template is overrideable at the device if it is bound to the
        device and we have not already overridden it.

        @param string uid: the unique id of a device
        @returns a list of all available templates for the given uid
        """
        obj = self._getObject(uid)
        templates = obj.getRRDTemplates()
        for template in templates:
            # see if the template is already overridden here
            if obj.id not in template.getPhysicalPath():
                try:
                    yield ITemplateNode(template)
                except UncataloguedObjectException:
                    pass

    def addLocationOrganizer(self, contextUid, id, description="", address=""):
        org = super(DeviceFacade, self).addOrganizer(
            contextUid, id, description
        )
        org.address = address
        return org

    def addDeviceClass(
        self, contextUid, id, description="", connectionInfo=None
    ):
        org = super(DeviceFacade, self).addOrganizer(
            contextUid, id, description
        )
        if connectionInfo:
            org.connectionInfo = connectionInfo
        return org

    def getModelerPluginDocStrings(self, uid):
        """
        Returns a dictionary of documentation for modeler plugins, indexed
        by the plugin name.
        """
        obj = self._getObject(uid)
        plugins = loadPlugins(obj)
        docs = {}
        packImporter = PackImporter()
        coreImporter = CoreImporter()
        for plugin in plugins:
            try:
                module = coreImporter.importModule(
                    plugin.package, plugin.modPath
                )
            except ImportError:
                try:
                    module = packImporter.importModule(
                        plugin.package, plugin.modPath
                    )
                except ImportError:
                    # unable to import skip over this one
                    continue
            pluginDocs = module.__doc__
            if pluginDocs:
                pluginDocs = (
                    "<pre>" + pluginDocs.replace("\n", "\n<br/>") + "</pre>"
                )
            docs[plugin.pluginName] = pluginDocs
        return docs

    def getConnectionInfo(self, uid):
        obj = self._getObject(uid)
        result = []
        deviceClass = obj
        if not isinstance(obj, DeviceClass):
            deviceClass = obj.deviceClass()
        for prop in deviceClass.primaryAq().getZ(
            "zCredentialsZProperties", []
        ):
            result.append(obj.exportZProperty(prop))
        return result

    def getGraphDefs(self, uid, drange):
        obj = self._getObject(uid)
        graphs = []
        # getGraphObjects is expected to return a tuple of size 2.
        # The graph definition and the context for that graph
        # definition.
        if hasattr(obj, "getGraphObjects"):
            for graph, ctx in obj.getGraphObjects():
                info = getMultiAdapter(
                    (graph, ctx), IMetricServiceGraphDefinition
                )
                # if there is a separate context display that as the title
                if ctx != obj:
                    info._showContextTitle = True
                graphs.append(info)
        return graphs

    def addIpRouteEntry(
        self,
        uid,
        dest,
        routemask,
        nexthopid,
        interface,
        routeproto,
        routetype,
        userCreated,
    ):
        device = self._getObject(uid)
        device.os.addIpRouteEntry(
            dest,
            routemask,
            nexthopid,
            interface,
            routeproto,
            routetype,
            userCreated,
        )

    def addIpInterface(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addIpInterface(newId, userCreated)

    def addOSProcess(self, uid, newClassName, example, userCreated):
        device = self._getObject(uid)
        device.os.addOSProcess(newClassName, example, userCreated)

    def addFileSystem(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addFileSystem(newId, userCreated)

    def addIpService(self, uid, newClassName, protocol, userCreated):
        device = self._getObject(uid)
        device.os.addIpService(newClassName, protocol, userCreated)

    def addWinService(self, uid, newClassName, userCreated):
        device = self._getObject(uid)
        device.os.addWinService(newClassName, userCreated)

    def getSoftware(self, uid):
        obj = self._getObject(uid)
        softwares = (IInfo(s) for s in obj.os.software.objectValuesGen())
        return softwares

    def getOverriddenObjectsList(self, uid, propname, relName="devices"):
        obj = self._getObject(uid)
        objects = []
        for inst in obj.getSubInstances(relName):
            if inst.isLocal(propname) and inst not in objects:
                proptype = inst.getPropertyType(propname)
                objects.append(
                    {
                        "devicelink": inst.getPrimaryDmdId(),
                        "props": self.maskPropertyPassword(inst, propname),
                        "proptype": proptype,
                    }
                )
                if relName == "devices":
                    objects[-1].update(
                        {
                            "objtype": relName,
                            "name": inst.titleOrId(),
                            "devicelink": inst.getPrimaryUrlPath(),
                        }
                    )
        for inst in obj.getOverriddenObjects(propname):
            proptype = inst.getPropertyType(propname)
            objects.append(
                {
                    "devicelink": inst.getPrimaryDmdId(),
                    "props": self.maskPropertyPassword(inst, propname),
                    "proptype": proptype,
                }
            )
        return objects

    def getOverriddenObjectsParent(self, uid, propname=""):
        obj = self._getObject(uid)
        if propname == "":
            prop = ""
            proptype = ""
        else:
            proptype = obj.getPropertyType(propname)
            prop = self.maskPropertyPassword(obj, propname)
        return [{"devicelink": uid, "props": prop, "proptype": proptype}]

    def getOverriddenZprops(self, uid, all=True, pfilt=iszprop):
        """
        Return list of device tree property names.
        If all use list from property root node.
        """
        obj = self._getObject(uid)
        if all:
            rootnode = obj.getZenRootNode()
        else:
            if obj.id == obj.dmdRootName:
                return []
            rootnode = aq_base(obj)
        return sorted(prop for prop in rootnode.propertyIds() if pfilt(prop))

    def clearGeocodeCache(self):
        """
        This clears the geocode cache by reseting the latlong property of
        all locations.
        """
        results = IModelCatalogTool(self._dmd.Locations).search(
            "Products.ZenModel.Location.Location"
        )
        for brain in results:
            try:
                brain.getObject().latlong = None
            except Exception:
                log.warn(
                    "Unable to clear the geocodecache from %s", brain.getPath()
                )

    @info
    def getGraphDefinitionsForComponent(self, uid):
        graphDefs = {}
        obj = self._getObject(uid)
        if isinstance(obj, ComponentGroup):
            components = obj.getComponents()
        else:
            components = list(
                getObjectsFromCatalog(obj.componentSearch, None, log)
            )

        for component in components:
            current_def = [
                graphDef.id for graphDef, _ in component.getGraphObjects()
            ]
            if component.meta_type in graphDefs:
                prev_def = graphDefs[component.meta_type]
                graphDefs[component.meta_type] = prev_def + list(
                    set(current_def) - set(prev_def)
                )
            else:
                graphDefs[component.meta_type] = current_def
        return graphDefs

    def getComponentGraphs(
        self, uid, meta_type, graphId, limit, graphsOnSame, allOnSame=False
    ):
        obj = self._getObject(uid)

        # get the components we are rendering graphs for
        query = {}
        query["meta_type"] = meta_type
        if isinstance(obj, ComponentGroup):
            components = [
                comp
                for comp in obj.getComponents()
                if comp.meta_type == meta_type
            ]
        else:
            components = list(
                getObjectsFromCatalog(obj.componentSearch, query, log)
            )

        graphDefault = None
        graphDict = {}
        # Find the graph for each component and a default graph for
        # components without one.
        for comp in components:
            for graph, _ in comp.getGraphObjects():
                if graph.id == graphId:
                    if not graphDefault:
                        graphDefault = graph
                    graphDict[comp.id] = graph
                    break
        if not graphDefault:
            return []

        if allOnSame:
            return [
                MultiContextMetricServiceGraphDefinition(
                    graphDefault, components, graphsOnSame
                )
            ]

        graphs = []
        for comp in components:
            graph = graphDict.get(comp.id)
            if graph:
                info = getMultiAdapter(
                    (graph, comp), IMetricServiceGraphDefinition
                )
                graphs.append(info)

        return {
            "data": graphs[limit["start"] : limit["end"]],
            "data_length": len(graphs),
        }

    def getDevTypes(self, uid):
        """
        Returns a list of devtypes for use for the wizard
        """
        devtypes = []
        org = self._getObject(uid)
        subOrgs = org.getSubOrganizers()
        # include the top level organizers in the list of device types
        organizers = [org] + subOrgs
        for org in organizers:
            org_name = org.getOrganizerName()
            org_id = org.getPrimaryId()
            if not hasattr(aq_base(org), "devtypes") or not org.devtypes:
                devtypes.append(
                    {
                        "value": org_id,
                        "description": org_name,
                        "protocol": "",
                    }
                )
                continue
            for t in org.devtypes:
                try:
                    desc, ptcl = t
                except ValueError:
                    continue

                # Both must be defined
                if not ptcl or not desc:
                    continue

                # special case for migrating from WMI to WinRM so we
                # can allow the zenpack to be backwards compatible
                # ZEN-19596:  Add support for Cluster and any sub-class for
                #             Windows and Cluster
                ms_dev_classes = (
                    "/Server/Microsoft/{}".format(cls)
                    for cls in ("Windows", "Cluster")
                )
                matched_org_to_dev_cls = any(
                    org_name.startswith(cls) for cls in ms_dev_classes
                )
                if matched_org_to_dev_cls and ptcl == "WMI":
                    ptcl = "WinRM"
                devtypes.append(
                    {
                        "value": org_id,
                        "description": desc,
                        "protocol": ptcl,
                    }
                )
        return sorted(devtypes, key=lambda x: x.get("description"))

    def getDeviceClasses(self, allClasses=True):
        """
        Get a list of device classes.

        If not allClasses, get only device classes which should use the
        standard device creation job.
        """
        devices = self._dmd.Devices
        deviceClasses = []
        user = getSecurityManager().getUser()

        def getOrganizerNames(org, user, deviceClasses):
            if (
                user.has_permission(ZEN_VIEW, org)
                and allClasses
                or org.getZ("zUsesStandardDeviceCreationJob", True)
            ):
                deviceClasses.append(org.getOrganizerName())
            for suborg in org.children(checkPerm=False):
                getOrganizerNames(suborg, user, deviceClasses)

        getOrganizerNames(devices, user, deviceClasses)
        deviceClasses.sort(key=lambda x: x.lower())
        return deviceClasses

    def getAllCredentialsProps(self):
        """
        Get a list of available credentials props
        """
        props = OrderedDict()
        for prop in self.context.dmd.Devices.zCredentialsZProperties:
            props[prop] = prop
        for org in self.context.dmd.Devices.getSubOrganizers():
            for prop in org.zCredentialsZProperties:
                props[prop] = (prop, org.exportZProperty(prop)["type"])
        return props.values()

    def maskPropertyPassword(self, inst, propname):
        prop = getattr(inst, propname)
        if inst.zenPropIsPassword(propname):
            prop = "*" * len(prop)
        return prop
