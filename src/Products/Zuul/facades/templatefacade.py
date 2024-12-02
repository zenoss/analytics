##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
from itertools import imap
from Acquisition import aq_parent
from zope.interface import implements
from Products.AdvancedQuery import Eq
from Products.ZenUtils.Utils import prepId
from Products import Zuul
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.interfaces import ITemplateFacade, ITemplateNode, IRRDDataSourceInfo, \
    IDataPointInfo, IThresholdInfo, IGraphInfo, IInfo, ITemplateLeaf, IGraphPointInfo
from Products.Zuul.infos.template import SNMPDataSourceInfo, CommandDataSourceInfo, DeviceClassTemplateNode
from Products.Zuul.utils import unbrain, safe_hasattr as hasattr, UncataloguedObjectException
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.Zuul.facades import ZuulFacade, ObjectNotFoundException
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.RRDDataSource import RRDDataSource
from Products.ZenModel.BasicDataSource import BasicDataSource
from Products.ZenModel.RRDDataPoint import RRDDataPoint
from Products.ZenModel.ThresholdClass import ThresholdClass
from Products.ZenModel.ThresholdGraphPoint import ThresholdGraphPoint
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.GraphPoint import GraphPoint
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenRRD.utils import rpneval

log = logging.getLogger('zen.TemplateFacade')

class TemplateFacade(ZuulFacade):
    implements(ITemplateFacade)

    @property
    def _root(self):
        return self._dmd.Devices

    def _getTemplateNodes(self):
        catalog = self._getCatalog('/zport/dmd/Devices')
        fields_to_return = [ "id" ]
        brains = catalog.search(types=RRDTemplate, fields=fields_to_return)
        nodes = {}
        # create 1 node for each template type
        for brain in brains:
            if brain.id not in nodes:
                try:
                    nodes[str(brain.id)] = ITemplateNode(brain.getObject())
                except UncataloguedObjectException:
                    pass
        for key in sorted(nodes.keys(), key=str.lower):
            yield nodes[key]

    def _getTemplateLeaves(self, id):
        obj = self._getObject(id)
        # search for all the templates with the same id
        query = Eq('id', obj.id)
        catalog = self._getCatalog('/zport/dmd/Devices')
        brains = catalog.search(types=RRDTemplate, query=query)
        templates = imap(unbrain, brains)
        for template in templates:
            try:
                # as our SOLR schema is case insensitive we check received id
                # with queried templates ids and yield only matched template.
                if template.id == obj.id:
                    yield ITemplateLeaf(template)
            except UncataloguedObjectException:
                pass

    def getTemplates(self, id):
        # see if we are asking for all templates
        if id == self._root.getPrimaryId():
            return  self._getTemplateNodes()
        # otherwise we are asking for instance of a template
        return self._getTemplateLeaves(id)

    def getTree(self, id):
        """
        Returns the root node for the template tree when the nodes are
        device classes
        """
        obj = self._getObject(id)
        try:
            return DeviceClassTemplateNode(obj)
        except UncataloguedObjectException:
            pass

    def getAddTemplateTargets(self, query=None):
        """
        @returns list of targets for our new template
        """
        cat = IModelCatalogTool(self._dmd)
        results = []
        # it can be any device class that we add the template too
        brains = cat.search(types=[DeviceClass])
        for brain in brains:
            # HACK: use the path to get the organizer name so we don't have to wake up the object
            label = brain.getPath()
            if label == "/zport/dmd/Devices":
                label = "/"
            else:
                label = label.replace("/zport/dmd/Devices/", "/")

            results.append(dict(uid=brain.getPath(), label=label))
        # the display is organizer name and we do not index it
        # so filter after the query
        if query is not None:
            results = [result for result in results if query.lower() in result['label'].lower()]
        return sorted(results, key=lambda org: org['label'])

    def addTemplate(self, id, targetUid):
        id = prepId(id)
        # make the assumption targetUid is always a device class
        parent = self._getObject(targetUid)
        relationship = parent.rrdTemplates
        relationship._setObject(id, RRDTemplate(id))
        template = getattr(relationship, id)
        node = ITemplateNode(template)
        leaf = ITemplateLeaf(template)
        node._addChild(leaf)
        return node

    def getObjTemplates(self, uid):
        obj = self._getObject(uid)
        return imap(IInfo, obj.getRRDTemplates())

    def makeLocalRRDTemplate(self, uid, templateName):
        obj = self._getObject(uid)
        if (templateName.startswith('/zport/dmd/')):
            templateName = self._getObject(templateName).id
        obj.makeLocalRRDTemplate(templateName)
        return obj.getRRDTemplateByName(templateName).getPrimaryId()

    def removeLocalRRDTemplate(self, uid, templateName):
        obj = self._getObject(uid)
        if (templateName.startswith('/zport/dmd/')):
            templateName = self._getObject(templateName).id
        obj.removeLocalRRDTemplate(templateName)
        return obj.getRRDTemplateByName(templateName).getPrimaryId()

    def _deleteObject(self, uid):
        """
        Deletes the object by getting the parent
        and then calling delete on the objects id.
        @param string uid Must be a valid path
        """
        obj = self._getObject(uid)
        context = aq_parent(obj)
        context._delObject(obj.id)

    def deleteTemplate(self, uid):
        return self._deleteObject(uid)

    def _removeDataPointFromGraphs(self, datapoint):
        template = datapoint.datasource().rrdTemplate()
        for graphDef in template.graphDefs():
            for point in graphDef.graphPoints():
                if (isinstance(point, DataPointGraphPoint)
                        and datapoint.name() == point.dpName):
                    self._deleteObject(point.getPrimaryId())

    def deleteDataSource(self, uid):
        """
        @param String uid: Unique Identifier of the data source we wish to delete
        """
        obj = self._getObject(uid)
        template = obj.rrdTemplate()
        for datapoint in obj.datapoints():
            self._removeDataPointFromGraphs(datapoint)
        template.manage_deleteRRDDataSources((obj.id,))

    def deleteDataPoint(self, uid):
        """
        @param String uid: Unique Identifier of the data point we wish to delete
        """
        obj = self._getObject(uid)
        datasource = obj.datasource()
        self._removeDataPointFromGraphs(obj)
        datasource.manage_deleteRRDDataPoints((obj.id,))

    def _editDetails(self, info, data):
        """
        Will apply every property in data to the info if
        it has that attribute
        @param IInfoBase (or descendant)
        @param Dictionary of the form {propertyName: propertyValue}
        @return IInfoBase with the properties changed
        """
        for key in data.keys():
            if hasattr(info, key):
                setattr(info, key, data[key])
        return info

    def getDataSources(self, uid):
        catalog = self._getCatalog(uid)
        infos = []
        if isinstance(catalog.context, RRDTemplate):
            brains = catalog.search(types=RRDDataSource)
            dataSources = imap(unbrain, brains)
            infos = imap(IRRDDataSourceInfo, dataSources)
        elif isinstance(catalog.context, RRDDataSource):
            brains = catalog.search(types=RRDDataPoint)
            dataPoints = imap(unbrain, brains)
            infos = imap(IDataPointInfo, dataPoints)
        return infos

    def _getDataSourceInfoFromObject(self, obj):
        """
        Given the obj this returns the correct info. We can not rely on
        adapt for datasources since we need different info objects depending on
        their type not the subclass.

        This defaults to using the adapters to return the correct info if not a datasource.
        """
        info = None

        # look for datasource type
        if isinstance(obj, BasicDataSource):
            if obj.sourcetype == 'SNMP':
                info = SNMPDataSourceInfo(obj)
            if obj.sourcetype == 'COMMAND':
                info = CommandDataSourceInfo(obj)

        # use the default adapter
        if not info:
            info = IInfo(obj)

        return info

    def getDataSourceDetails(self, uid):
        """
        Given the unique id of the datasource we will
        return an IDataSourceInfo (or subclass) that has the properties populated
        @param string uid absolute id of the datasource
        @returns IDataSourceInfo
        """
        obj = self._getObject(uid)
        return self._getDataSourceInfoFromObject(obj)

    def setInfo(self, uid, data):
        """
        Given a dictionary of {property name: property value}
        this will populate the datapoint
        @param string uid unique identifier of the object we are editing
        @param Dictionary of properties to update
        @return IInfo with the updated properties
        """
        obj = self._getObject(uid)
        info = self._getDataSourceInfoFromObject(obj)

        # see if we need to rename the object
        # (if you change this also update TemplateRouter)
        newId = None
        if 'newId' in data:
            newId = data['newId']
            del data['newId']
            info.rename(newId)

        return self._editDetails(info, data)

    def getDataPointDetails(self, uid):
        """
        @param string unique Identifier of a datapoint
        @returns IDataPointInfo
        """
        obj = self._getObject(uid)
        return IDataPointInfo(obj)

    def getThresholds(self, uid):
        catalog = self._getCatalog(uid)
        brains = catalog.search(types=ThresholdClass)
        thresholds = imap(unbrain, brains)
        return imap(IThresholdInfo, thresholds)

    def getThresholdDetails(self, uid):
        """
        @param String uid: the id of the threshold
        @returns IThresholdInfo
        """
        threshold = self._getObject(uid)
        template = threshold.rrdTemplate()
        info = IInfo(threshold)
        # don't show the "selected one" in the list of avaialble
        info.allDataPoints = [point for point in template.getRRDDataPointNames()]
        return info

    def addDataPoint(self, dataSourceUid, name):
        """
        Adds a datapoint to the datasource specified by the UID
        @param string dataSourceUid unique identifier of a datasource
        @parma string name
        """
        datasource = self._getObject(dataSourceUid)
        return datasource.manage_addRRDDataPoint(str(name))

    def addDataSource(self, templateUid, name, type):
        """
        Adds a datasource to a template
        @param string templateUid unique identifier of the template
        @param string name name of our datasource
        @param string type must be a valid datasource type (see RRDTemplate getDataSourceOptions)
        """
        template = self._getObject(templateUid)

        # get our option information based on the string type inputed
        selectedOption = None
        options = template.getDataSourceOptions() # comes back in a (name, typeinformation) tuple
        for option in options:
            if option[0] == type:
                selectedOption = option[1]

        if selectedOption is None:
            raise Exception("%s is not a valid DataSource Type" % type)

        # create the datasource and return it
        datasource = template.manage_addRRDDataSource(name, selectedOption)
        return datasource

    def _getDummyTemplate(self):
        """
        This returns the first template found in the template catalog.
        This method should only be called when you know at least one exists.
        """
        return self._dmd.searchRRDTemplates()[0].getObject()

    def getDataSourceTypes(self):
        """
        @returns [] List of all of the datasource types (in string form)
        """
        data = []
        template = self._getDummyTemplate()
        for name, dsOption in template.getDataSourceOptions():
            data.append({'type': name})
        return data

    def getThresholdTypes(self):
        data = []
        template = self._getDummyTemplate()
        for pythonClass, type in template.getThresholdClasses():
            data.append({'type': type})
        return data

    def addThreshold(self, uid, thresholdType, thresholdId, dataPoints=None):

        thresholdId = prepId(thresholdId)
        template = self._getObject(uid)
        thresholds = template.thresholds
        for pythonClass, key in template.getThresholdClasses():
            if key == thresholdType:
                thresholds._setObject(thresholdId, pythonClass(thresholdId))
                break
        else:
            raise Exception('Unknown threshold type: %s' % thresholdType)
        threshold = getattr(thresholds, thresholdId)
        dsnames = self._translateDataPoints(dataPoints)
        threshold._updateProperty('dsnames', dsnames)
        return threshold

    def _translateDataPoints(self, dataPoints):
        """ Takes the list of datapoints from te server
        and turns them into the proper dsnames that the
        threshold items expects
        @param List dataPointsUids
        @return List proper names from the dataPoint object
        """
        dsnames = []
        for dataPointUid in dataPoints:
            dataPoint = self._getObject(dataPointUid)
            dsnames.append( dataPoint.name() )
        return dsnames

    def removeThreshold(self, uid):
        """Removes the threshold
        @param string uid
        """
        # look through all the graph definitions and remove any where the
        # threshold point matches the threshold we are deleting
        obj = self._getObject(uid)
        template = obj.rrdTemplate()
        for graphDef in template.graphDefs():
            for point in graphDef.graphPoints():
                if isinstance(point, ThresholdGraphPoint) and point.threshId == obj.id:
                    self._deleteObject(point.getPrimaryId())

        # finally delete the threshold
        return self._deleteObject(uid)

    def getGraphs(self, uid):
        catalog = self._getCatalog(uid)
        brains = catalog.search(types=GraphDefinition)
        graphs = map(IGraphInfo, imap(unbrain, brains))
        graphs.sort(key=lambda graph: graph.sequence)
        return graphs.__iter__()

    def addDataSourceToGraph(self, dataSourceUid, graphUid, includeThresholds=False):
        datasource = self._getObject(dataSourceUid)
        for dp in datasource.datapoints():
            self.addDataPointToGraph(dp.getPrimaryId(), graphUid, includeThresholds)

    def addDataPointToGraph(self, dataPointUid, graphUid, includeThresholds=False):
        if isinstance(dataPointUid, basestring):
            uids = [dataPointUid]
        else:
            uids = dataPointUid
        datapoints = [self._getObject(u) for u in uids]
        graph = self._getObject(graphUid)
        return graph.manage_addDataPointGraphPoints([d.name() for d in datapoints], includeThresholds)

    def getCopyTargets(self, uid, query=''):
        catalog = IModelCatalogTool(self._dmd)
        template = self._getObject(uid)
        types = ['Products.ZenModel.DeviceClass.DeviceClass']
        brains = catalog.search(types=types)
        objs = imap(unbrain, brains)
        def genTargets():
            for obj in objs:
                container = obj.rrdTemplates
                organizer = '/' + '/'.join(obj.getPrimaryPath()[4:])
                label = organizer
                if template.id in container.objectIds():
                    label += " (%s)" % _t('Create Copy')
                if label.lower().startswith(query.lower()):
                    uid = '/'.join(obj.getPrimaryPath())
                    yield dict(uid=uid, label=label)
        def byLabel(left, right):
            return cmp(left['label'].lower(), right['label'].lower())
        return sorted(genTargets(), byLabel)

    def copyTemplate(self, uid, targetUid):
        template = self._getTemplate(uid)
        target = self._getObject(targetUid)
        marker = object()
        source = getattr(template, 'device', marker)
        if source is marker and isinstance(target, DeviceClass):
            # copying to and from a DeviceClass
            source = template.deviceClass()
            source.manage_copyAndPasteRRDTemplates((template.id,), targetUid)
        else:
            if isinstance(target, DeviceClass):
                # copying from a Device to a DeviceClass
                container = target.rrdTemplates
            else:
                # copying from either to a Device
                container = target
            if template.id in container.objectIds():
                msg = '"%s" already contains template "%s".'
                args = (targetUid, template.id)
                raise Exception(msg % args)
            copy = template._getCopy(container)
            container._setObject(copy.id, copy)

    def addGraphDefinition(self, templateUid, graphDefinitionId):
        template = self._getTemplate(templateUid)
        return template.manage_addGraphDefinition(graphDefinitionId)

    def deleteGraphDefinition(self, uid):
        graphDefinition = self._getObject(uid)
        template = graphDefinition.rrdTemplate()
        template.manage_deleteGraphDefinitions((graphDefinition.id,))

    def deleteGraphPoint(self, uid):
        """
        Deletes a graph point
        """
        graphPoint = self._getObject(uid)
        graphDef = graphPoint.graphDef()
        graphDef.manage_deleteGraphPoints((graphPoint.id,))

    def getGraphPoints(self, uid):
        graphDefinition = self._getObject(uid)
        graphPoints = graphDefinition.getGraphPoints()
        for graphPoint in graphPoints:
            yield IGraphPointInfo(graphPoint)

    def getInfo(self, uid):
        """
        @param uid unique identifier of an object
        @returns the info object as identified by the UID
        """
        obj = self._getObject(uid)
        return IInfo(obj)

    def addThresholdToGraph(self, graphUid, thresholdUid):
        graphDefinition = self._getObject(graphUid)
        thresholdClass = self._getThresholdClass(thresholdUid)
        return graphDefinition.manage_addThresholdGraphPoints((thresholdClass.id,))

    def addCustomToGraph(self, graphUid, customId, customType):
        graphDefinition = self._getObject(graphUid)
        return graphDefinition.manage_addCustomGraphPoint(customId, customType)

    _graphInstructionTypes = (('DefGraphPoint', 'DEF'),
                              ('VdefGraphPoint', 'VDEF'),
                              ('CdefGraphPoint', 'CDEF'),
                              ('PrintGraphPoint', 'PRINT'),
                              ('GprintGraphPoint', 'GPRINT'),
                              ('CommentGraphPoint', 'COMMENT'),
                              ('VruleGraphPoint', 'VRULE'),
                              ('HruleGraphPoint', 'HRULE'),
                              ('LineGraphPoint', 'LINE'),
                              ('AreaGraphPoint', 'AREA'),
                              ('TickGraphPoint', 'TICK'),
                              ('ShiftGraphPoint', 'SHIFT'))

    def getGraphInstructionTypes(self):
        for pythonClassName, label in self._graphInstructionTypes:
            yield dict(pythonClassName=pythonClassName, label=label)

    def setGraphPointSequence(self, uids):
        for i, uid in enumerate(uids):
            graphPoint = self._getGraphPoint(uid)
            graphPoint.sequence = i

    def getGraphDefinition(self, uid):
        obj = self._getObject(uid)
        if not isinstance(obj, GraphDefinition):
            raise Exception('Cannot find GraphDefinition at "%s".' % uid)
        return IInfo(obj)

    def setGraphDefinition(self, uid, data):
        graphDef = self._getObject(uid)
        Zuul.unmarshal(data, graphDef)


    def _setGraphDefinitionSequence(self, uids):
        for i, uid in enumerate(uids):
            graphDefinition = self.getGraphDefinition(uid)
            graphDefinition.sequence = i

    def _getCatalog(self, uid):
        obj = self._getObject(uid)
        return IModelCatalogTool(obj)

    def _getTemplate(self, uid):
        obj = self._getObject(uid)
        if not isinstance(obj, RRDTemplate):
            raise Exception('Cannot find RRDTemplate at "%s".' % uid)
        return obj

    def _getThresholdClass(self, uid):
        obj = self._getObject(uid)
        if not isinstance(obj, ThresholdClass):
            raise Exception('Cannot find ThresholdClass at "%s".' % uid)
        return obj

    def _getGraphPoint(self, uid):
        obj = self._getObject(uid)
        if not isinstance(obj, GraphPoint):
            raise Exception('Cannot find GraphPoint at "%s".' % uid)
        return obj

    def getCollectorTemplate(self):
        """
        Returns the tree representation of a
        collector template
        """
        templates = []
        collectorTemplate = self._getObject('/zport/dmd/Monitors/rrdTemplates/PerformanceConf')
        templates.append(ITemplateNode(collectorTemplate))
        try:
            hubTemplate = self._getObject('/zport/dmd/Monitors/Hub/rrdTemplates/HubConf')
            templates.append(ITemplateNode(hubTemplate))
        except ObjectNotFoundException:
            pass
        return templates
 
    def getDataPointsRPNValues(self, maxval, thuid, selecteddps, minval):
        threshold = self._getObject(thuid)
        dpsrpn = []
        for point in selecteddps:
            dpParams = {}
            for graph in threshold.rrdTemplate.getGraphDefs():
                dpParams.update({
                    'rpnvalue': pobj.rpn if pobj.rpn else ''
                    for pobj in graph.getDataPointGraphPoints(point)
                })
            dpParams['name'] = point
            #if we can't use rpn to the entered values, return raw values back
            try:
                dpParams.update({'maxrpn': rpneval(maxval, dpParams.get('rpnvalue', ''))})
            except Exception:
                dpParams.update({'maxrpn': maxval})
            try:
                dpParams.update({'minrpn': rpneval(minval, dpParams.get('rpnvalue', ''))})
            except Exception:
                dpParams.update({'minrpn': minval})
            dpsrpn.append(dpParams)
        return dpsrpn
