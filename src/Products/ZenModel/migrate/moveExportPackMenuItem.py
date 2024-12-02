##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class MoveExportPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    

    def cutover(self, dmd):

        # Remove "Export ZenPack" item from the ZenPack menu.
        zenPackMenu = dmd.zenMenus._getOb('ZenPack', None)
        if zenPackMenu and \
            zenPackMenu.zenMenuItems._getOb('exportZenPack', None):
            zenPackMenu.zenMenuItems._delObject('exportZenPack')

        # Add to the More menu
        moreMenu = dmd.zenMenus._getOb('More', None)
        if moreMenu:
            moreMenu.manage_addZenMenuItem(
                id='exportZenPack',
                description='Export ZenPack...',
                action='dialog_exportPack',
                permissions=('Manage DMD',),
                isdialog=True,
                isglobal=True,
                ordering=1.01,
                allowed_classes=('ZenPack',))


MoveExportPackMenuItem()
