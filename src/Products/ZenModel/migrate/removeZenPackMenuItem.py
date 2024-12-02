##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class RemoveZenPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        items = dmd.zenMenus.ZenPack_list.zenMenuItems
        if hasattr(items, 'removeZenPack'):        
            dmd.zenMenus.ZenPack_list.zenMenuItems._delObject('removeZenPack')
        if hasattr(items, 'deleteZenPack'):        
            dmd.zenMenus.ZenPack_list.zenMenuItems._delObject('deleteZenPack')


RemoveZenPackMenuItem()
