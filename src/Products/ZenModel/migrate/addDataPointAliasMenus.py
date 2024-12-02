##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
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

class addDataPointAliasMenus(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'DataPointProperties_list': [
                     {  'action': 'dialog_removeDataPointAlias',
                        'isdialog': True,
                        'description': 'Remove Data Point Alias...',
                        'id': 'removeDataPointAlias',
                        'ordering': 90,
                        'permissions': ('Change Device',)},
                     {  'action': 'dialog_addDataPointAlias',
                        'isdialog': True,
                        'description': 'Add Data Point Alias...',
                        'id': 'addDataPointAlias',
                        'ordering': 100,
                        'permissions': ('Change Device',)},
                     ]} )
        
        addMenuItems( dmd, 'SimpleDataPoint_list', [
                     {  'action': 'dialog_removeDataPointAlias',
                        'isdialog': True,
                        'description': 'Remove Data Point Alias...',
                        'id': 'removeDataPointAlias',
                        'ordering': 90,
                        'permissions': ('Change Device',)},
                     {  'action': 'dialog_addDataPointAlias',
                        'isdialog': True,
                        'description': 'Add Data Point Alias...',
                        'id': 'addDataPointAlias',
                        'ordering': 100,
                        'permissions': ('Change Device',)},
                     ] )
        

        
addDataPointAliasMenus()
