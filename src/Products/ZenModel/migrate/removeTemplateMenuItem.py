##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

def addMenuItems( dmd, menuId, menuItems ):
    dsMenu = dmd.zenMenus._getOb( menuId, None)        
    for menuItem in menuItems:
        if dsMenu and not dsMenu.zenMenuItems._getOb( menuItem['id'], None):
            dsMenu.manage_addZenMenuItem( **menuItem )


class removeTemplateMenuItem(Migrate.Step):
    version = Migrate.Version(3, 0, 0)
    
    def cutover(self, dmd):
        
        items = dmd.zenMenus._getOb('PerformanceMonitor_list').zenMenuItems
        if hasattr(items, 'performanceTemplates'):        
            items._delObject('performanceTemplates')
        addMenuItems( dmd, 'PerformanceMonitor_list', [
                {  'action': 'rrdTemplates/PerformanceConf/viewRRDTemplate',
                    'description': 'Performance Template',
                    'id': 'performanceConf',
                    'isdialog': False,
                    'isglobal': True,
                    'ordering': 16.0,
                    'permissions': ('View Device',) } ] )


removeTemplateMenuItem()
