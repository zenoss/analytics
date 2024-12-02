##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.ZenModel.DeviceReportClass import DeviceReportClass
from Products.ZenModel.CustomDeviceReportClass import CustomDeviceReportClass
from Products.ZenModel.GraphReportClass import GraphReportClass

# graphReports is using buildMenus so we let it go first before we modify
# some of the same menus.

class BaseReportClasses(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        def BuildOrSwitchReportClass(rcId, reportClass):        
            rc = getattr(dmd.Reports, rcId, None)
            if rc:
                if not isinstance(rc, reportClass):
                    rc.__class__ = reportClass
            else:
                rc = reportClass(rcId)
                dmd.Reports._setObject(rc.id, rc)
            return rc
        
        BuildOrSwitchReportClass('Device Reports', DeviceReportClass)
        BuildOrSwitchReportClass('Custom Device Reports', CustomDeviceReportClass)
        BuildOrSwitchReportClass('Graph Reports', GraphReportClass)
        
        # Menus

        reportList = dmd.zenMenus.Report_list
        reportList.zenMenuItems.addDeviceReport.allowed_classes = ['CustomDeviceReportClass']
        reportList.zenMenuItems.deleteDeviceReports.allowed_classes = [
            'CustomDeviceReportClass', 'GraphReportClass', 'MultiGraphReportClass']


BaseReportClasses()
