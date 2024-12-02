##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class ImportExportZenPacks(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        zenPackListMenu = dmd.zenMenus.ZenPack_list
        if zenPackListMenu.zenMenuItems._getOb('installZenPack',None):
            zenPackListMenu.zenMenuItems._delObject('installZenPack')
        zenPackListMenu.manage_addZenMenuItem(
                id='installZenPack',
                description='Install ZenPack...',
                action='dialog_installZenPack',
                isdialog=True,
                permissions=('Manage DMD',),
                ordering=1.00)

ImportExportZenPacks()
