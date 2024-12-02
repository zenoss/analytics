##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
log = logging.getLogger('zen.ReportFacade')

from zope.interface import implements
from zope.component import getMultiAdapter
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import ITreeFacade, IReportFacade, IMetricServiceGraphDefinition
from Products.Zuul.routers.report import reportTypes, essentialReportOrganizers
from Products.Zuul.infos.metricserver import MultiGraphReportGraphDefinition

_createMethods = [
    'manage_addDeviceReport',
    'manage_addGraphReport',
    'manage_addMultiGraphReport',
]

class ReportFacade(TreeFacade):
    implements(IReportFacade, ITreeFacade)

    @property
    def _report_factories(self):
        factories = getattr(self, '_report_factory_methods', None)
        if factories is None:
            factories = {}
            for reportType, orgUid, methodName in zip(reportTypes,
                    essentialReportOrganizers, _createMethods):
                organizer = self._dmd.restrictedTraverse(orgUid)
                factories[reportType] = getattr(organizer, methodName)
            self._report_factory_methods = factories
        return factories

    @property
    def _root(self):
        return self._dmd.Reports

    def moveNode(self, sourceUid, targetUid):
        targetNode = self._dmd.restrictedTraverse(targetUid)
        movingNode = self._dmd.restrictedTraverse(sourceUid)

        # make sure object being moved does not have duplicate id
        # with an existing object in the targetNode
        if movingNode.id in targetNode:
            msgfields = {
                'title': movingNode.titleOrId(),
                'target': targetNode.titleOrId(),
                'dupeId': movingNode.id,
            }
            failmsg = "Cannot move '%(title)s', '%(target)s' already contains an object with the id '%(dupeId)s'" % msgfields
            raise Exception(failmsg)

        # all clear, move the object from parent to the target node
        movingNode.getParentNode()._delObject(movingNode.id)
        targetNode._setObject(movingNode.id, movingNode)

    def addReport(self, reportType, contextUid, id):
        report = self._report_factories[reportType](id)
        report.getParentNode()._delObject(id)
        targetNode = self._dmd.restrictedTraverse(contextUid)
        targetNode._setObject(id, report)

    def getGraphReportDefs(self, uid):
        obj = self._getObject(uid)
        defs = []
        for element in obj.getElements():
            component = element.getComponent()
            if not component:
                log.warning("%s is missing a component, skipping", element)
                continue
            try:
                info = getMultiAdapter((element.getGraphDef(), component), IMetricServiceGraphDefinition)
            except AttributeError:
                # if they remove or move a graphdef then we might not
                # be able to find it
                log.warning("%s has an invalid graph definition, skipping", element)
                continue
            defs.append(info)
        return defs

    def getMultiGraphReportDefs(self, uid, graphGroup=None):
        obj = self._getObject(uid)
        graphs = []
        for graphDef in obj.getDefaultGraphDefs(graphGroup=graphGroup):
            if graphDef['separateGraphs']:
                info = getMultiAdapter((graphDef['graphDef'], graphDef['context'], graphDef['collection']), IMetricServiceGraphDefinition)
            else:
                # specialized adapter for combined graph groups
                info = MultiGraphReportGraphDefinition(graphDef['graphDef'], graphDef['context'], graphDef['collection'])
            graphs.append(info)
        return graphs
