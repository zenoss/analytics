##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import sys
from App.special_dtml import DTMLFile
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenModel.ZenossSecurity import *
from zope.interface import implements
from Acquisition import aq_parent
from ZenModelRM import ZenModelRM
from Products.ZenModel.interfaces import IIndexed

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.RRDDataSource import SimpleRRDDataSource
from Products.ZenModel.BasicDataSource import BasicDataSource
from Products.ZenModel.BuiltInDS import BuiltInDS
from Products.ZenModel.PingDataSource import PingDataSource
from Products.ZenModel.ConfigurationError import ConfigurationError
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.ZenUtils.Utils import importClass
from Products.ZenWidgets import messaging
from RRDDataPoint import SEPARATOR
from ZenPackable import ZenPackable

import logging
log = logging.getLogger('zen.RRDTemplate')

RRDTEMPLATE_CATALOG = 'searchRRDTemplates'


def CreateRRDTemplatesCatalog(dmd, rebuild=False):
    """
    Create the searchRRDTemplates catalog if it does not already exist.
    Return the catalog.
    """
    from Products.ZCatalog.ZCatalog import manage_addZCatalog
    from Products.ZenUtils.Search import makeCaseSensitiveFieldIndex, \
                                            makePathIndex
    zcat = getattr(dmd, RRDTEMPLATE_CATALOG, None)
    if zcat and rebuild:
        dmd._delObject(RRDTEMPLATE_CATALOG)
        zcat = None
    if zcat is None:
        manage_addZCatalog(dmd, RRDTEMPLATE_CATALOG, RRDTEMPLATE_CATALOG)
        zcat = dmd._getOb(RRDTEMPLATE_CATALOG)
        cat = zcat._catalog
        cat.addIndex('id', makeCaseSensitiveFieldIndex('id'))
        cat.addIndex('getPhysicalPath', makePathIndex('getPhysicalPath'))
    return zcat


def YieldAllRRDTemplates(root, criteria=None):
    """
    Yield all templates in the searchRRDTemplates catalog which fall under
    the given root and match the given criteria.  To get all RRDTemplates
    pass dmd in as root.  If criteria contains a
    value for getPhysicalRoot then the root parameter will be ignored.

    If the searchRRDTemplates catalog is not present then fall back to using
    DeviceClass.getAllRRDTemplatesPainfully().  In this case root must
    be a DeviceClass and criteria is ignored. (This is compatible with
    previous DeviceClass.getAllRRDTemplates usage.)

    The searchRRDTemplates catalog was added in 2.2
    """
    zcat = getattr(root, RRDTEMPLATE_CATALOG, None)
    if zcat is not None:
        criteria = criteria or {}
        criteria.setdefault('getPhysicalPath', root.getPrimaryId())
        brains = zcat(criteria)
        for result in brains:
            yield result.getObject()
    else:
        for t in root.getAllRRDTemplatesPainfully():
            yield t


def manage_addRRDTemplate(context, id, REQUEST = None):
    """make a RRDTemplate"""
    tt = RRDTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


addRRDTemplate = DTMLFile('dtml/addRRDTemplate',globals())


def crumbspath(templ, crumbs, idx=-1):
    """Create the crumbs path for sub objects of an RRDTemplate.
    """
    return crumbs


class RRDTemplate(ZenModelRM, ZenPackable):

    implements(IIndexed)
    meta_type = 'RRDTemplate'

    default_catalog = RRDTEMPLATE_CATALOG

    security = ClassSecurityInfo()

    description = ""
    targetPythonClass = "Products.ZenModel.Device"

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'targetPythonClass', 'type':'string', 'mode':'w'},
        )

    # The graphs relationship can be removed post 2.1.  It is needed
    # by the graphDefinitionAndFriends migrate script for 2.1

    _relations =  ZenPackable._relations + (
        ("deviceClass", ToOne(
            ToManyCont,"Products.ZenModel.TemplateContainer", "rrdTemplates")),
        ("datasources", ToManyCont(
            ToOne,"Products.ZenModel.RRDDataSource", "rrdTemplate")),
        ("graphs", ToManyCont(
            ToOne,"Products.ZenModel.RRDGraph", "rrdTemplate")),
        ("thresholds", ToManyCont(
            ToOne,"Products.ZenModel.ThresholdClass", "rrdTemplate")),
        ("graphDefs", ToManyCont(
            ToOne,"Products.ZenModel.GraphDefinition", "rrdTemplate")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = (
    {
        'immediate_view' : 'viewRRDTemplate',
        'actions'        :
        (
            { 'id'            : 'overview'
            , 'name'          : 'Performance Template'
            , 'action'        : 'viewRRDTemplate'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(RRDTemplate, self).breadCrumbs(terminator)
        return crumbspath(self, crumbs)


    def isEditable(self, context):
        """Is this template editable in context.
        """
        return ((context == self or context.isLocalName(self.id))
                and self.checkRemotePerm(ZEN_CHANGE_DEVICE, self))


    def getGraphDefs(self):
        ''' Return an ordered list of the graph definitions
        '''
        def graphDefSortKey(a):
            try:
                return int(a.sequence)
            except ValueError:
                return sys.maxint
        return sorted(self.graphDefs(), key=graphDefSortKey)


    def getRRDPath(self):
        """Return the path on which this template is defined.
        """
        return self.getPrimaryParent().getPrimaryDmdId(subrel="rrdTemplates")


    def getGraphableThresholds(self):
        ''' Return a list of names of graphable thresholds
        '''
        return [t for t in self.thresholds()]


    def getRRDDataPointNames(self):
        """Return the list of all datapoint names.
        """
        # We check for the presence of datapoints on the datasources
        # to better handle situation where the datasource is broken
        # (usually because of a missing zenpack.)
        datasources = [ds for ds in self.datasources()
                        if hasattr(ds, 'datapoints')]
        return [dp.name() for ds in datasources for dp in ds.datapoints()]


    def getRRDDataSources(self, dsType=None):
        """Return a list of all datapoints on this template.
        """
        if dsType is None: return self.datasources()
        return [ds for ds in self.datasources()
                if ds.sourcetype == dsType
                or (dsType=='COMMAND' and ds.useZenCommand())]


    def getRRDDataPoints(self):
        """Return a list of all datapoints on this template.
        """
        result = []
        for s in self.datasources():
            result.extend(s.datapoints())
        return result


    def getRRDDataPoint(self, name):
        """Return a datapoint based on its name.
        """
        # see ZEN-16251 because of th underscore in datasource name
        # iterate through every datapoint we have until we have one that matches the
        # name.
        for ds in self.datasources():
            for dp in ds.datapoints():
                if dp.name() == name:
                    return dp
        raise ConfigurationError('Unknown data point "%s"' % name)

    security.declareProtected('Add DMD Objects', 'manage_addRRDDataSource')
    def manage_addRRDDataSource(self, id, dsOption, REQUEST=None):
        """Add an RRDDataSource to this DeviceClass.
        """
        ds = None
        if id and dsOption:
            ds = self.getDataSourceInstance(id, dsOption)
            self.datasources._setObject(ds.id, ds)
            ds = self.datasources._getOb(ds.id)
            if ds:
                ds.addDataPoints()
        if REQUEST:
            if ds:
                messaging.IMessageSender(self).sendToBrowser(
                    'Datasource Added',
                    "Data source %s added" % ds.id
                )
                url = '%s/datasources/%s' % (self.getPrimaryUrlPath(), ds.id)
                return REQUEST['RESPONSE'].redirect(url)
            else:
                return self.callZenScreen(REQUEST)
        return ds


    def getTargetPythonClass(self):
        """
        Returns the python class object that this template can be bound to.
        """
        from Products.ZenModel.Device import Device
        cname = getattr(self, "targetPythonClass", None)
        if cname:
            try:
                return importClass(cname)
            except ImportError:
                log.exception("Unable to import class " + cname)
        return Device


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteRRDDataSources')
    def manage_deleteRRDDataSources(self, ids=(), REQUEST=None):
        """Delete RRDDataSources from this DeviceClass
        """
        def clean(rel, id):
            for obj in rel():
                if id in obj.dsnames:
                    obj.dsnames.remove(id)
                    if not obj.dsnames:
                        rel._delObject(obj.id)

        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            self._p_changed = True
            if getattr(self.datasources,id,False):
                self.datasources._delObject(id)
                clean(self.graphs, id)
                clean(self.thresholds, id)

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Datasources Deleted',
                'Datasource%s %s deleted.' % ('' if len(ids)==1 else 's',
                                              ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Add DMD Objects', 'manage_addRRDThreshold')
    def manage_addRRDThreshold(self, id, thresholdClassName, REQUEST=None):
        """Add an RRDThreshold to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        org = self.getThresholdClass(id, thresholdClassName)
        self.thresholds._setObject(org.id, org)
        org = self.thresholds._getOb(org.id)
        if REQUEST:
            if org:
                messaging.IMessageSender(self).sendToBrowser(
                    'Threshold Added',
                    'Threshold "%s" added' % org.id
                )
                url = '%s/thresholds/%s' % (self.getPrimaryUrlPath(), org.id)
                return REQUEST['RESPONSE'].redirect(url)
            else:
                return self.callZenScreen(REQUEST)
        return org


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteRRDThresholds')
    def manage_deleteRRDThresholds(self, ids=(), REQUEST=None):
        """Delete RRDThresholds from this DeviceClass
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if getattr(self.thresholds,id,False):
                self.thresholds._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Thresholds Deleted',
                'Threshold%s %s deleted.' % ('' if len(ids)==1 else 's',
                                              ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addGraphDefinition')
    def manage_addGraphDefinition(self, new_id, REQUEST=None):
        """Add a GraphDefinition to our RRDTemplate.
        """
        from GraphDefinition import GraphDefinition
        self.getGraphDefs()
        graph = None
        graph = GraphDefinition(new_id)
        graph.sequence = len(self.graphDefs())
        self.graphDefs._setObject(graph.id, graph)
        graph = self.graphDefs._getOb(graph.id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Added',
                'Graph "%s" added' % graph.id
            )
            url = '%s/graphDefs/%s' % (self.getPrimaryUrlPath(), graph.id)
            return REQUEST['RESPONSE'].redirect(url)
        return graph


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_deleteGraphDefinitions')
    def manage_deleteGraphDefinitions(self, ids=(), REQUEST=None):
        """Remove GraphDefinitions from this RRDTemplate.
        """
        for id in ids:
            self.graphDefs._delObject(id)
            self.manage_resequenceGraphDefs()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Graphs Deleted',
                'Graph%s %s deleted.' % ('' if len(ids)==1 else 's',
                                              ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_resequenceGraphDefs')
    def manage_resequenceGraphDefs(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequence of the GraphDefinitions.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.getGraphDefs(),
                            seqmap, origseq, REQUEST)


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataSourcesToGraphs')
    def manage_addDataSourcesToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Create GraphPoints for all datapoints in the given datasources (ids)
        in each of the graphDefs (graphIds.)
        If a graphpoint already exists for a datapoint in a graphDef then
        don't create a 2nd one.
        """
        newGraphPoints = []
        for dsId in ids:
            ds = self.datasources._getOb(dsId, None)
            if ds:
                newGraphPoints += ds.manage_addDataPointsToGraphs(
                    [dp.id for dp in ds.datapoints()],
                    graphIds)
        numAdded = len(newGraphPoints)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Points Added',
                'Added %s GraphPoint%s' % (numAdded, numAdded != 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)
        return newGraphPoints


    security.declareProtected(ZEN_MANAGE_DMD, 'manage_addDataSourcesToGraphs')
    def manage_addThresholdsToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Create GraphPoints for all given thresholds that are not already
        graphed. in the given datasources (ids)
        """
        newGps = []
        for graphId in graphIds:
            graphDef = self.graphDefs._getOb(graphId, None)
            if graphDef:
                for threshId in ids:
                    thresh = self.thresholds._getOb(threshId, None)
                    if thresh and not graphDef.isThresholdGraphed(thresh.id):
                        newGps += graphDef.manage_addThresholdGraphPoints(
                                                                [thresh.id])
        if REQUEST:
            numAdded = len(newGps)
            messaging.IMessageSender(self).sendToBrowser(
                'Graph Points Added',
                'Added %s GraphPoint%s' % (numAdded, numAdded != 1 and 's' or '')
            )
            return self.callZenScreen(REQUEST)
        return newGps


    def getDataSourceClasses(self):
        dsClasses = [BasicDataSource, BuiltInDS, PingDataSource]
        for zp in self.dmd.ZenPackManager.packs():
            dsClasses += zp.getDataSourceClasses()
        return dsClasses


    def getDataSourceOptions(self):
        ''' Returns a list of the available datasource options as a list
        of (display name, dsOption)
        '''
        dsTypes = []
        for dsClass in self.getDataSourceClasses():
            dsTypes += [(t, '%s.%s' % (dsClass.__name__, t))
                            for t in dsClass.sourcetypes]
        return dsTypes


    def getDataSourceInstance(self, id, dsOption):
        ''' Given one of the dsOptions returned by getDataSourceOptions)
        return an instance of the that RRDDataSource subclass.
        '''
        dsClassName, dsType = dsOption.split('.')
        for c in self.getDataSourceClasses():
            if dsClassName == c.__name__:
                ds = c(id)
                ds.sourcetype = dsType
                break
        else:
            raise ConfigurationError('Cannot find datasource class'
                        ' for %s' % dsOption)
        return ds


    def getThresholdClasses(self):
        from Products.ZenModel.MinMaxThreshold import MinMaxThreshold
        from Products.ZenModel.ValueChangeThreshold import ValueChangeThreshold
        thresholdClasses = [MinMaxThreshold, ValueChangeThreshold]
        for zp in self.dmd.ZenPackManager.packs():
            try:
                thresholdClasses += zp.getThresholdClasses()
            except Exception as e:
                log.exception("Unable to fetch thresholds from zenpack %s, please try reinstalling the zenpack. Error %s", zp, e)
        return map(lambda x: (x, x.__name__), thresholdClasses)


    def getThresholdClass(self, id, thresholdClassName):
        ''' Given one of the dsOptions returned by getDataSourceOptions)
        return an instance of the that RRDDataSource subclass.
        '''
        for c, name in self.getThresholdClasses():
            if thresholdClassName == c.__name__:
                return c(id)
        raise ConfigurationError('Cannot find threshold class %s' %
                                 thresholdClassName)


    def getEventClassNames(self):
        """
        Get a list of all event class names within the permission scope.
        """
        return self.primaryAq().Events.getOrganizerNames()


    def getUIPath(self, separator='/'):
        """
        Given a separator and a template this method returns the UI path that we display
        to the user.
        @param RRDTemplate template
        @param String separator e.g. '/'
        @returns String e.g. '/Devices' or '/Server'
        """
        obj = self.deviceClass()
        if obj is None:
            obj = aq_parent(self)
            path = list(obj.getPrimaryPath())
            # remove the "devices" relationship
            path.pop(path.index('devices'))
            if isinstance(obj, DeviceComponent):
                # remove the component relationship
                comp_rel = obj.getParentNode().id
                path.pop(path.index(comp_rel))
            else:
                # this template is in a Device
                path = path[:-1]
                path.append(obj.titleOrId())
        else:
            # this template is in a DeviceClass.rrdTemplates relationship
            path = list(obj.getPrimaryPath())[:-1]
            path.append(obj.titleOrId())
        parts = path[4:]
        return separator + separator.join(parts)


InitializeClass(RRDTemplate)
