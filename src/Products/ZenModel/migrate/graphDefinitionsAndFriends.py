##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint
from Products.ZenModel.ConfigurationError import ConfigurationError

class GraphDefinitionsAndFriends(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    scriptVersion = 1.3
    scriptVerAttrName = 'newGraphsVers'
    
    def __init__(self):
        Migrate.Step.__init__(self)
        import thresholds
        self.dependencies = [thresholds.thresholds]


    def cutover(self, dmd):
                
        # Build Reports/Graph Reports
        if not hasattr(dmd.Reports, 'Graph Reports'):
            dmd.Reports.manage_addReportClass('Graph Reports')
                
        # Install new menus
        dmd.buildMenus({  
            'GraphPoint_list': [ 
                {  'action': 'dialog_addDataPointGraphPoint',
                   'description': 'Add DataPoint...',
                   'id': 'addGPFromDataPoint',
                   'isdialog': True,
                   'ordering': 90.50,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_addThresholdGraphPoint',
                   'description': 'Add Threshold...',
                   'id': 'addGPFromThreshold',
                   'isdialog': True,
                   'ordering': 90.49,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_addCustomGraphPoint',
                   'description': 'Add Custom...',
                   'id': 'addGPCustom',
                   'isdialog': True,
                   'ordering': 90.49,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_deleteGraphPoint',
                   'description': 'Delete GraphPoint...',
                   'id': 'deleteGraphPoint',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)},
                {  'action': "javascript:submitFormToMethod('graphPointList', 'manage_resequenceGraphPoints')",
                   'description': 'Re-sequence GraphPoints',
                   'id': 'resequenceGraphPoints',
                   'ordering': 80.0,
                   'permissions': ('Change Device',)}
            ],
        'Graph_list_noseq': [  {  'action': 'dialog_addGraph',
                   'description': 'Add Graph...',
                   'id': 'addGraph',
                   'isdialog': True,
                   'ordering': 90.1,
                   'permissions': ('Change Device',)},
                {  'action': 'dialog_deleteGraph',
                   'description': 'Delete Graph...',
                   'id': 'deleteGraph',
                   'isdialog': True,
                   'ordering': 90.0,
                   'permissions': ('Change Device',)}],
            })

        prevVersion = getattr(dmd, self.scriptVerAttrName, 0)

        # Change the action on the Re-sequence Graphs menu item
        reseqMenuItem = dmd.zenMenus.Graph_list.zenMenuItems.resequenceGraphs
        reseqMenuItem.action = reseqMenuItem.action.replace(
                                                'RRDGraphs', 'GraphDefs')

        # RRDTemplate.graphDefs needs to be built
        numTemplatesConverted = 0
        numGraphs = 0
        numDataPointsFound = 0
        numDataPointsMissing = 0
        lineTypesFixed = 0
        
        for template in dmd.Devices.getAllRRDTemplates():
            template.buildRelations()
            
            # This code is only for when you want to complete delete
            # all graph definitions from all templates and remigrate
            # from the old RRDGraphs
            #for gdId in template.graphDefs.objectIds():
            #    template.graphDefs._delObject(gdId)
                        
            if template.graphDefs():
                lineTypesFixed += self.fixDefaultLineTypes(template)
                self.fixStackedGraphPoints(template, prevVersion)
                self.fixLegends(template, prevVersion)
                self.fixLineTypes(template, prevVersion)
                self.fixGraphPointNames(template, prevVersion)
                self.fixCustom(template, prevVersion)
                # Might need to build the reports relation
                for g in template.graphDefs():
                    g.buildRelations()
            else:
                g, f, m = self.convertTemplate(template)
                numGraphs += g
                numDataPointsFound += f
                numDataPointsMissing += m
                numTemplatesConverted += 1

        setattr(dmd, self.scriptVerAttrName, self.scriptVersion)

        #print('converted %s templates, %s graphs, %s datapoints; '
        #        '%s datapoints missing; %s lineTypes fixed' % 
        #        (numTemplatesConverted, numGraphs, 
        #        numDataPointsFound, numDataPointsMissing, lineTypesFixed))



    def fixDefaultLineTypes(self, template):
        numFixed = 0
        for graphDef in template.graphDefs():
            for gp in graphDef.graphPoints():
                if hasattr(gp, 'lineType') and not gp.lineType:
                    gp.lineType = gp.LINETYPE_DONTDRAW
                    numFixed += 1
        return numFixed


    def fixStackedGraphPoints(self, template, prevVersion):
        if prevVersion < 1.0:
            for graphDef in template.graphDefs():
                oldGraph = template.graphs._getOb(graphDef.id, None)
                if not oldGraph:
                    continue
                for gp in graphDef.graphPoints():
                    gp.stacked = oldGraph.stacked


    def fixLegends(self, template, prevVersion):
        if prevVersion < 1.2:
            for graphDef in template.graphDefs():
                for gp in graphDef.graphPoints():
                    try:
                        del gp.legend
                    except AttributeError:
                        pass


    def fixGraphPointNames(self, template, prevVersion):
        if prevVersion < 1.2:
            for graphDef in template.graphDefs():
                idChanges = []
                for gp in graphDef.graphPoints():
                    if isinstance(gp,DataPointGraphPoint) and gp.id==gp.dpName:
                        newName = gp.dpName.split('_', 1)[-1]
                        idChanges.append((gp, newName))
                for gp, newId in idChanges:
                    if newId not in graphDef.graphPoints.objectIds():
                        graphDef.graphPoints._delObject(gp.id)
                        gp.id = newId
                        graphDef.graphPoints._setObject(gp.id, gp)
            

    def fixLineTypes(self, template, prevVersion):
        if prevVersion < 1.2:
            for graphDef in template.graphDefs():
                isFirstDP = True
                for gp in graphDef.graphPoints():
                    if isinstance(gp, DataPointGraphPoint):
                        try:
                            dp = template.getRRDDataPoint(gp.dpName)
                        except ConfigurationError:
                            dp = None
                        except AttributeError:
                            dp = None
                        if dp:
                            gp.lineType = (dp.linetype or 
                                            (gp.stacked and gp.LINETYPE_AREA) or
                                            (isFirstDP and gp.LINETYPE_AREA) or
                                            gp.LINETYPE_LINE)
                        isFirstDP = False


    def fixCustom(self, template, prevVersion):
        if prevVersion < 1.3:
            for g in template.graphDefs():
                if g.custom:
                    for gp in g.graphPoints():
                        if isinstance(gp, DataPointGraphPoint):
                            g.custom = g.custom.replace(gp.dpName, gp.id)


    def convertTemplate(self, template):
        numGraphs = 0
        numDataPointsFound = 0
        numDataPointsMissing = 0
        for rrdGraph in template.graphs():
            numGraphs += 1
            graphDef = GraphDefinition(rrdGraph.id)
            template.graphDefs._setObject(graphDef.id, graphDef)
            graphDef = getattr(template.graphDefs, graphDef.id)
            graphDef.sequence = rrdGraph.sequence
            graphDef.height = rrdGraph.height
            graphDef.width = rrdGraph.width
            graphDef.units = rrdGraph.units
            graphDef.log = rrdGraph.log
            graphDef.base = rrdGraph.base
            graphDef.summary = rrdGraph.summary
            graphDef.hasSummary = rrdGraph.hasSummary
            graphDef.miny = rrdGraph.miny
            graphDef.maxy = rrdGraph.maxy
            graphDef.custom = rrdGraph.custom
            isFirst = True
            for dsName in rrdGraph.dsnames:
                try:
                    dp = template.getRRDDataPoint(dsName)
                    numDataPointsFound += 1
                except ConfigurationError:
                    dp = None
                    numDataPointsMissing += 1
                except AttributeError as e:
                    msg = ('There was a problem converting the graph %s.'
                            % rrdGraph.id +
                            ' This might be caused by a misinstalled zenpack,'
                            ' make sure all zenpacks listed on the ZenPacks'
                            ' page (under Settings) are properly installed. '
                            + str(e))
                    raise msg
                includeThresholds = not graphDef.custom                     
                gp = graphDef.manage_addDataPointGraphPoints(
                                    [dsName], includeThresholds)[0]
                if graphDef.custom:
                    graphDef.custom = graphDef.custom.replace(dsName, gp.id)
                if dp:
                    gp.color = dp.color
                    gp.stacked = rrdGraph.stacked
                    if graphDef.custom:
                        gp.lineType = gp.LINETYPE_DONTDRAW
                    else:
                        gp.lineType = (dp.linetype or 
                                        (gp.stacked and gp.LINETYPE_AREA) or
                                        (isFirst and gp.LINETYPE_AREA) or
                                        gp.LINETYPE_LINE)
                    gp.format = dp.format
                    gp.limit = dp.limit
                    gp.rpn = dp.rpn
                isFirst = False
        # Remove the rrdGraphs
        # Keep them for now, remove in 2.2
        #for graphId in template.graphs.objectIds():
        #    template.graphs._delObject(graphId)
        return (numGraphs, numDataPointsFound, numDataPointsMissing)
            
                

GraphDefinitionsAndFriends()
