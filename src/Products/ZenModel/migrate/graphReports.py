##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.GraphReportClass import GraphReportClass
# Dependency?


class GraphReports(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    

    def cutover(self, dmd):
        
        # Build Reports/Graph Reports
        rc = getattr(dmd.Reports, 'Graph Reports', None)
        if rc:
            if not isinstance(rc, GraphReportClass):
                rc.__class__ = GraphReportClass
        else:
            rc = GraphReportClass('Graph Reports')
            dmd.Reports._setObject(rc.id, rc)
                
        # Build menus
        if hasattr(dmd.zenMenus, 'GraphReportElement_list'):
            dmd.zenMenus._delObject('GraphReportElement_list')
        elementList = dmd.zenMenus.manage_addZenMenu('GraphReportElement_list')
        elementList.manage_addZenMenuItem(
                id='deleteGraph',
                description='Delete Graph...', 
                action='dialog_deleteGraphReportElement', 
                permissions=('Change Device',), 
                isdialog=True, 
                ordering=90.0)
        elementList.manage_addZenMenuItem(
                id='resequenceGraphs',
                description='Re-sequence Graphs', 
                action="javascript:submitFormToMethod('graphReportElementListform', 'manage_resequenceGraphReportElements')", 
                permissions=('Change Device',), 
                isdialog=False, 
                ordering=80.0)
                
        reportList = dmd.zenMenus.Report_list
        reportList.manage_addZenMenuItem(
                id='addGraphReport',
                description='Add Graph Report...',
                action='dialog_addGraphReport',
                permissions=('Change Device',),
                allowed_classes=('GraphReportClass',),
                isdialog=True,
                ordering=89)
        reportList.zenMenuItems.deleteDeviceReports.description = 'Delete Reports...'
        reportList.zenMenuItems.moveDeviceReports.description = 'Move Reports...'


GraphReports()
