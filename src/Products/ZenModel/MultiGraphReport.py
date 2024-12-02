##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.deprecated import deprecated
from Products.ZenModel.BaseReport import BaseReport
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Utils import resequence, getDisplayType
from ZenossSecurity import ZEN_MANAGE_DMD
from Products.ZenWidgets import messaging


@deprecated
def manage_addMultiGraphReport(context, id, REQUEST = None):
    """ Create a new MultiGraphReport
    """
    gr = MultiGraphReport(id)
    context._setObject(gr.id, gr)
    if REQUEST is not None:
        audit('UI.Report.Add', gr.id, reportType=getDisplayType(gr), organizer=context)
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class MultiGraphReport(BaseReport):

    meta_type = "MultiGraphReport"

    numColumns = 1
    numColumnsOptions = (1, 2, 3)

    _properties = BaseReport._properties + (
        {'id':'numColumns', 'type':'int', 
            'select_variable' : 'numColumnOptions', 'mode':'w'},
    )

    _relations =  (
        ('collections', 
            ToManyCont(ToOne, 'Products.ZenModel.Collection', 'report')),
        ("graphGroups", 
            ToManyCont(ToOne,"Products.ZenModel.GraphGroup", "report")),
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'report')),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : '',
            'actions'        :
            ( 
                {'name'          : 'View Report',
                'action'        : '',
                'permissions'   : ("View",),
                },
                {'name'          : 'Edit Report',
                'action'        : 'editMultiGraphReport',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def getBreadCrumbUrlPath(self):
        """
        Return the url to be used in breadcrumbs for this object.
        """
        return self.getPrimaryUrlPath() + '/editMultiGraphReport'


    ### Graph Groups
    
    security.declareProtected('Manage DMD', 'manage_addGraphGroup')
    def manage_addGraphGroup(self, new_id, collectionId='', graphDefId='',
                                                                REQUEST=None):
        """ Add a new graph group
        """
        from GraphGroup import GraphGroup
        gg = GraphGroup(new_id, collectionId, graphDefId, 
                                            len(self.graphGroups()))
        self.graphGroups._setObject(gg.id, gg)
        gg = self.graphGroups._getOb(gg.id)
        if REQUEST:
            audit('UI.Report.AddGraphGroup', self.id, graphGroup=gg.id)
            return REQUEST['RESPONSE'].redirect(
                '%s/graphGroups/%s' % (self.getPrimaryUrlPath(), gg.id))
        return gg


    security.declareProtected('Manage DMD', 'manage_deleteGraphGroups')
    def manage_deleteGraphGroups(self, ids=(), REQUEST=None):
        """ Delete graph groups from this report
        """
        for id in ids:
            self.graphGroups._delObject(id)
        self.manage_resequenceGraphGroups()
        if REQUEST:
            for id in ids:
                audit('UI.Report.DeleteGraphGroup', self.id, graphGroup=id)
            messaging.IMessageSender(self).sendToBrowser(
                'Groups Deleted',
                'Group%s deleted: %s' % (len(ids) > 1 and 's' or '',
                                         ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceGraphGroups')
    def manage_resequenceGraphGroups(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequence of the groups.
        """
        retval = resequence(self, self.graphGroups(), seqmap, origseq, REQUEST)
        if REQUEST:
            audit('UI.Report.ResequenceGraphGroups', self.id, sequence=seqmap, oldData_={'sequence':origseq})
        return retval


    def getGraphGroups(self):
        """get the ordered groups
        """
        return sorted(self.graphGroups(), key=lambda a: a.sequence)

    ### Collections

    security.declareProtected('Manage DMD', 'getCollections')
    def getCollections(self):
        """ Return an alpha ordered list of available collections
        """
        return sorted(self.collections(), key=lambda a: a.id)
        

    security.declareProtected('Manage DMD', 'manage_addCollection')
    def manage_addCollection(self, new_id, REQUEST=None):
        """Add a collection
        """
        from Collection import Collection
        col = Collection(new_id)
        self.collections._setObject(col.id, col)
        col = self.collections._getOb(col.id)
        if REQUEST:
            audit('UI.Report.AddCollection', self.id, collection=col.id)
            url = '%s/collections/%s' % (self.getPrimaryUrlPath(), new_id)
            return REQUEST['RESPONSE'].redirect(url)
        return col

    security.declareProtected('Manage DMD', 'manage_deleteCollections')
    def manage_deleteCollections(self, ids=(), REQUEST=None):
        """ Delete collections from this report
        """
        for id in ids:
            self.collections._delObject(id)
        if REQUEST:
            for id in ids:
                audit('UI.Report.DeleteCollection', self.id, collection=id)
            messaging.IMessageSender(self).sendToBrowser(
                'Collections Deleted',
                'Collection%s deleted: %s' % (len(ids) > 1 and 's' or '',
                                         ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    ### Graph Definitions
         
    security.declareProtected(ZEN_MANAGE_DMD, 'getGraphDefs')
    def getGraphDefs(self):
        """ Return an ordered list of the graph definitions
        """
        def graphDefSortKey(a):
            try:
                return int(a.sequence)
            except ValueError:
                return sys.maxint
        return sorted(self.graphDefs(), key=graphDefSortKey)


    def getGraphDef(self, graphDefId):
        """ Retrieve the given graph def
        """
        rc = getattr(self.dmd.Reports, 'Multi-Graph Reports', None)
        if rc:
            return getattr(rc.graphDefs, graphDefId, None)
        return None


    security.declareProtected('Manage DMD', 'manage_addGraphDefinition')
    def manage_addGraphDefinition(self, new_id, REQUEST=None):
        """Add a GraphDefinition 
        """
        from GraphDefinition import GraphDefinition
        graph = GraphDefinition(new_id)
        graph.sequence = len(self.graphDefs())
        self.graphDefs._setObject(graph.id, graph)
        graph = self.graphDefs._getOb(graph.id)
        if REQUEST:
            audit('UI.Report.AddGraphDefinition', self.id, graphDefinition=graph.id)
            url = '%s/graphDefs/%s' % (self.getPrimaryUrlPath(), graph.id)
            return REQUEST['RESPONSE'].redirect(url)
        return graph
        

    security.declareProtected('Manage DMD', 'manage_deleteGraphDefinitions')
    def manage_deleteGraphDefinitions(self, ids=(), REQUEST=None):
        """Remove GraphDefinitions 
        """
        for id in ids:
            self.graphDefs._delObject(id)
            self.manage_resequenceGraphDefs()
        if REQUEST:
            for id in ids:
                audit('UI.Report.DeleteGraphDefinition', self.id, graphDefinition=id)
            messaging.IMessageSender(self).sendToBrowser(
                'Graphs Deleted',
                'Graph%s deleted: %s' % (len(ids) > 1 and 's' or '',
                                         ', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceGraphDefs')
    def manage_resequenceGraphDefs(self, seqmap=(), origseq=(), REQUEST=None):
        """ Reorder the sequence of the GraphDefinitions.
        """
        from Products.ZenUtils.Utils import resequence
        retval = resequence(self, self.getGraphDefs(), seqmap, origseq, REQUEST)
        if REQUEST:
            audit('UI.Report.ResequenceGraphDefinitions', self.id, sequence=seqmap, oldData_={'sequence':origseq})
        return retval

    ### Graphing
    

    def getDefaultGraphDefs(self, drange=None, graphGroup=None):
        """ Construct the list of graph dicts for this report.
        Similar in functionality to MetricMixin.getDefaultGraphDefs
        """
        graphs = []
        for gg in self.getGraphGroups():
            if graphGroup and gg.id != graphGroup:
                continue
            collection = gg.getCollection()
            things = collection and collection.getDevicesAndComponents()
            graphDef = gg.getGraphDef()
            if not things or not graphDef:
                continue
            if gg.combineDevices:
                graphs.append(dict(context=things, graphDef=graphDef, collection=collection, separateGraphs=False))
            else:
                for thing in things:
                    graphs.append(dict(context=thing, graphDef=graphDef, collection=collection, separateGraphs=True))
        return graphs


InitializeClass(MultiGraphReport)
