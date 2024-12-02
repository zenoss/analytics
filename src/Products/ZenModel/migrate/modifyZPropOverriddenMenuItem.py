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

class modifyZPropOverriddenMenuItem(Migrate.Step):
    version = Migrate.Version(3, 0, 0)
    
    def cutover(self, dmd):
        
        items = dmd.zenMenus._getOb('More').zenMenuItems
        if hasattr(items, 'overriddenObjects'):        
            items._delObject('overriddenObjects')
        addMenuItems( dmd, 'More', [
                {  'action': 'zPropOverridden',
                    'allowed_classes': ['DeviceClass'],
                    'description': 'Overridden Objects',
                    'id': 'overriddenObjects',
                    'ordering': 21.0,
                    'permissions': ('zProperties View',) } ] )
        if hasattr(items, 'overriddenObjects_new'):        
            items._delObject('overriddenObjects_new')
        addMenuItems( dmd, 'More', [
                {  'action': 'zPropOverriddenNew',
                    'allowed_classes': ['EventClass'],
                    'description': 'Overridden Objects',
                    'id': 'overriddenObjects_new',
                    'ordering': 21.0,
                    'permissions': ('zProperties View',) } ] )
        if hasattr(items, 'viewHistory'):        
            items._delObject('viewHistory')
        addMenuItems( dmd, 'More', [
                {  'action': 'viewHistory',
                    'banned_classes': ('IpNetwork',),
                    'allowed_classes': ['Device', 'System', 'DeviceGroup', 'Location', 'DeviceClass'],
                    'description': 'Modifications',
                    'id': 'viewHistory',
                    'ordering': 2.0,
                    'permissions': ('View History',) } ] )
        if hasattr(items, 'viewHistory_new'):        
            items._delObject('viewHistory_new')
        addMenuItems( dmd, 'More', [
                {  'action': 'viewNewHistory',
                    'banned_classes': ('IpNetwork',),
                    'allowed_classes': ['EventClass'],
                    'description': 'Modifications',
                    'id': 'viewHistory_new',
                    'ordering': 2.0,
                    'permissions': ('View History',) } ] )


modifyZPropOverriddenMenuItem()
