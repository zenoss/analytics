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

class ZenPackMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):  
        zpm = dmd.zenMenus.manage_addZenMenu('ZenPack')
        zpm.manage_addZenMenuItem( action='dialog_deletePackable', 
                                   description='Delete from ZenPack...', 
                                   id='deleteFromZenPack', 
                                   isdialog=True, 
                                   ordering=1.02, 
                                   permissions=('Manage DMD',))
        zpm.manage_addZenMenuItem( action='dialog_exportPack', 
                                  description='Export ZenPack...', 
                                  id='exportZenPack', 
                                  isdialog=True, 
                                  ordering=1.01, 
                                  permissions=('Manage DMD',))
                                   

ZenPackMenus()
