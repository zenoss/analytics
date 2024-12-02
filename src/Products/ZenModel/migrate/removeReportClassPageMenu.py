##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZenossSecurity import *

class RemoveReportClassPageMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        # Build menus
        dmd.buildMenus({
        'More': [ {  'action': 'dialog_addOneToZenPack',
                     'allowed_classes': ['ZenPackable'],
                     'banned_classes': ('DeviceGroup',
                                        'IpNetwork',
                                        'Location',
                                        'System',
                                        'RRDDataSource',
                                        'RRDDataPoint',
                                        'ThresholdClass',
                                        'GraphDefinition',
                                        'GraphPoint',
                                        'ReportClass',
                                        ),
                     'description': 'Add to ZenPack...',
                     'id': 'addToZenPack',
                     'isdialog': True,
                     'ordering': 1.0,
                     'permissions': (ZEN_MANAGE_DMD,) } ]
        })  
        
        am = dmd.zenMenus._getOb('Add', None)
        if am:
            if am.zenMenuItems._getOb('addDeviceReport', False):
                am.zenMenuItems._delObject('addDeviceReport')
            if am.zenMenuItems._getOb('addReportClass', False):
                am.zenMenuItems._delObject('addReportClass')


RemoveReportClassPageMenu()
