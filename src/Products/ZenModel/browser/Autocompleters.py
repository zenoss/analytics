##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Five.browser import BrowserView
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenUtils.jsonutils import json
from Products.ZenUtils.Utils import formreq, getObjByPath
from Products.AdvancedQuery import Eq, MatchGlob


class DeviceNames(BrowserView):
    """
    Provides device names for autocompleter population.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, query='', dataRoot='devices'):
        """
        @param query: A glob by which to filter device names
        @type query: str
        @return: A JSON representation of a list of ids
        @rtype: "['id1', 'id2', 'id3']"
        """
        if dataRoot != 'devices':
            import exceptions
            raise exceptions.ValueError("dataRoot should only be 'devices'")

        query_scope = self.context.dmd.Devices
        query = MatchGlob('name', query.rstrip('*') + '*')
        if isinstance(self.context, DeviceOrganizer):
            query_scope = self.context
        catalog = IModelCatalogTool(query_scope).devices
        brains = catalog.search(query=query, fields=['name'])

        return  sorted((b.name for b in brains),
                        key=lambda x: x.lower())


class ComponentPaths(BrowserView):
    """
    Get component paths and names associated with a given device or group of
    devices.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, deviceIds=()):
        """
        @param deviceIds: One ore more device ids under which components should be
        sought
        @type deviceIds: str
        @return: A JSON representation of a list of tuples describing components
        under devices specified
        @rtype: "[('/path/to/comp1', 'comp1'), ...]"
        """
        paths = set()
        if isinstance(deviceIds, basestring):
            deviceIds = [deviceIds]
        for devId in deviceIds:
            d = self.context.findDevice(devId)
            if d:
                for comp in d.getReportableComponents():
                    name = comp.name
                    if callable(name):
                        name = name()
                    paths.add((comp.getPrimaryId(), name))

        return sorted(paths, key=lambda x: x[1].lower())


class GraphIds(BrowserView):
    """
    Get a list of the graph defs available for the given device
    and component.

    Adapts DeviceClasses.
    """
    @json
    @formreq
    def __call__(self, deviceIds=(), componentPaths=()):
        """
        @param deviceIds: One ore more device ids under which graphs should be
        sought
        @type deviceIds: str, list
        @param componentPaths: Path(s) to components under which graphs should
        be sought
        @type componentPaths: str, list
        @return: A JSON representation of a list of ids
        @rtype: "['id1', 'id2', 'id3']"
        """
        graphIds = set()
        if isinstance(deviceIds, basestring):
            deviceIds = [deviceIds]
        if isinstance(componentPaths, basestring):
            componentPaths = [componentPaths]
        if not componentPaths:
            componentPaths = ('',)
        for devId in deviceIds:
            thing = self.context.findDevice(devId)
            if thing:
                for compPath in componentPaths:
                    if compPath:
                        thing = getObjByPath(thing, compPath)
                    for t in thing.getRRDTemplates():
                        for g in t.getGraphDefs():
                            graphIds.add(g.id)
        return sorted(graphIds)


class ServiceList(BrowserView):
    """
    Get a list of id and descriptions for a live search

    """
    @json
    @formreq
    def __call__(self, dataRoot='serviceclasses'):
        """
        @param dataRoot: The name of the relation under which services should
        be sought
        @type dataRoot: str
        @return: A JSON representation of a list of service ids
        @rtype: "['id1', 'id2', ...]"
        """
        liveSearchList = []
        for srv in self.context.getSubInstancesGen(rel='serviceclasses'):
            if getattr(srv, 'description', None):
                liveSearchList.append('%s [%s]' % (srv.id, srv.description))
            else:
                liveSearchList.append(srv.id)
        return liveSearchList


class EventClassNames(BrowserView):
    """
    Get a list of all event classes that match the filter.
    """
    @json
    @formreq
    def __call__(self):
        """
        @return: A JSON representation of a list of paths
        @rtype: "['/path/1', '/path/2', ...]"
        """
        orgs = self.context.dmd.Events.getSubOrganizers()
        paths = ('/'.join(x.getPrimaryPath()) for x in orgs)
        return [p.replace('/zport/dmd','') for p in paths]


class OrganizerNames(BrowserView):
    """
    Return the organizer names to which this user has access
    """
    @json
    @formreq
    def __call__(self, dataRoot="Devices"):
        """
        @return: A JSON representation of a list of organizers
        @rtype: "['/Systems/Sys1', '/Groups/Group1', ...]"
        """
        root = self.context.dmd.getDmdRoot(dataRoot)
        return root.getOrganizerNames()
