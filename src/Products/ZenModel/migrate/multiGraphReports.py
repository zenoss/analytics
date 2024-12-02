##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.MultiGraphReportClass import MultiGraphReportClass
from Products.ZenModel.MultiGraphReport import MultiGraphReport
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint

# graphReports is using buildMenus so we let it go first before we modify
# some of the same menus.
import graphReports
from Products.ZenUtils.Utils import unused
unused(graphReports)

class MultiGraphReports(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    scriptVersion = 1.1
    scriptVerAttrName = 'multiGraphReportsVers'

    def cutover(self, dmd):

        prevVersion = getattr(dmd, self.scriptVerAttrName, 0)

        # Build Reports/MultiGraph Reports
        frc = getattr(dmd.Reports, 'Multi-Graph Reports', None)
        if frc:
            if not isinstance(frc, MultiGraphReportClass):
                frc.__class__ = MultiGraphReportClass
        else:
            frc = MultiGraphReportClass('Multi-Graph Reports')
            dmd.Reports._setObject(frc.id, frc)
        dmd.Reports.buildRelations()
        
        # Get rid of the graphDefs relation on MultiGraphReportClass
        # and add to the reports
        def BuildRelationsOnReports(reportClass):
            reportClass.buildRelations()
            for report in reportClass.reports():
                report.buildRelations()
            for subClass in reportClass.children():
                BuildRelationsOnReports(subClass)
        BuildRelationsOnReports(dmd.Reports['Multi-Graph Reports'])


        def WalkGraphPoints(reportClass):
            for report in reportClass.reports():
                if isinstance(report, MultiGraphReport):
                    for graphDef in report.graphDefs():
                        for gp in graphDef.graphPoints():
                            yield gp
            for subClass in reportClass.children():
                for gp in WalkGraphPoints(subClass):
                    yield gp

        # Fix Legends
        if prevVersion < 1.0:
            for gp in WalkGraphPoints(dmd.Reports):
                if hasattr(gp, 'legend'):
                    gp.legend = gp.DEFAULT_MULTIGRAPH_LEGEND
        if prevVersion < 1.1:
            for gp in WalkGraphPoints(dmd.Reports):
                if hasattr(gp,'legend') and not hasattr(gp.__class__, 'legend'):
                    del gp.legend

        # Fix DPGP names
        if prevVersion < 1.0:
            idChanges = []
            for gp in WalkGraphPoints(dmd.Reports):
                if isinstance(gp, DataPointGraphPoint):
                    newId = gp.id.split('_', 1)[-1]
                    idChanges.append((gp, newId))
            for gp, newId in idChanges:
                if newId not in gp.graphDef.graphPoints.objectIds():
                    gp.graphDef.graphPoints._delObject(gp.id)
                    gp.id = newId
                    gp.graphDef.graphPoints._setObject(gp.id, gp)


        # Get rid of old  Report menus
        reportList = dmd.zenMenus.Report_list
        if hasattr(reportList, 'addMultiGraphReport'):
            reportList.manage_deleteZenMenuItem(('addMultiGraphReport',))
        reportList.manage_addZenMenuItem( 
                id='addMultiGraphReport',
                description='Add Multi-Graph Report...', 
                action='dialog_addMultiGraphReport', 
                permissions=('Change Device',), 
                isdialog=True, 
                allowed_classes=('MultiGraphReportClass',),
                ordering=88.0)        
        
        if hasattr(dmd.zenMenus, 'collectionList'):
            dmd.zenMenus._delObject('collectionList')
        collectionList = dmd.zenMenus.manage_addZenMenu('collectionList')
        collectionList.manage_addZenMenuItem(
                id='addCollection',
                description='Add Collection...', 
                action='dialog_addCollection', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)
        collectionList.manage_addZenMenuItem(
                id='deleteCollections',
                description='Delete Collections...', 
                action='dialog_deleteCollections', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=87.0)

        if hasattr(dmd.zenMenus, 'collectionItemList'):
            dmd.zenMenus._delObject('collectionItemList')
        collectionList = dmd.zenMenus.manage_addZenMenu('collectionItemList')
        collectionList.manage_addZenMenuItem(
                id='deleteCollectionItems',
                description='Delete Items...', 
                action='dialog_deleteCollectionItems', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)
        collectionList.manage_addZenMenuItem(
                id='resequenceCollectionItem',
                description='Re-sequence Items', 
                action="javascript:submitFormToMethod('collectionItemForm', 'manage_resequenceCollectionItems')", 
                permissions=('Change Device',), 
                isdialog=False, 
                ordering=87.0)

        if hasattr(dmd.zenMenus, 'GraphGroup_list'):
            dmd.zenMenus._delObject('GraphGroup_list')
        collectionList = dmd.zenMenus.manage_addZenMenu('GraphGroup_list')
        collectionList.manage_addZenMenuItem(
                id='addGraphGroup',
                description='Add Group...', 
                action='dialog_addGraphGroup', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=89.0)
        collectionList.manage_addZenMenuItem(
                id='deleteGraphGroups',
                description='Delete Group...', 
                action='dialog_deleteGraphGroups', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=88.0)
        collectionList.manage_addZenMenuItem(
                id='resequenceCollectionItem',
                description='Re-sequence Items', 
                action="javascript:submitFormToMethod('graphGroupForm', 'manage_resequenceGraphGroups')", 
                permissions=('Change Device',), 
                isdialog=False, 
                ordering=87.0)

        setattr(dmd, self.scriptVerAttrName, self.scriptVersion)

MultiGraphReports()
