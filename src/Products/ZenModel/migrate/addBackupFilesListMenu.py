##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


class AddBackupFilesListMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)


    def cutover(self, dmd):


        # Create the BackupFiles_list menu    
        dmd.buildMenus({  
            'BackupFiles_list': [ 
                {  'action': 'dialog_deleteBackup',
                   'description': 'Delete Backup...',
                   'id': 'deleteBackup',
                   'isdialog': True,
                   'ordering': 90.50,
                   'permissions': ('Change Device',)},
            ],
        })


AddBackupFilesListMenu()
