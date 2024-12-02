##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class RestoreRemoveZenPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        
        zpMenu = getattr(dmd.zenMenus, 'ZenPack_list', None)
        if zpMenu:
            # Remove existing
            if zpMenu.zenMenuItems._getOb('removeZenPack', None):
                zpMenu.zenMenuItems._delObject('removeZenPack')

            # Recreate
            zpMenu.manage_addZenMenuItem(
                id='removeZenPack',
                description='Delete ZenPack...',
                action='dialog_removeZenPacks',
                isdialog=True,
                permissions=('Manage DMD',),
                ordering=1.0
                )

RestoreRemoveZenPackMenuItem()
