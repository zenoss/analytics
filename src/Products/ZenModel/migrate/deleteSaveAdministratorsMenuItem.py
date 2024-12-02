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

class DeleteSaveAdministratorsMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if hasattr(dmd.zenMenus.Administrator_list.zenMenuItems, 
            'saveAdministrators'):  
            dmd.zenMenus.Administrator_list.manage_deleteZenMenuItem(
                'saveAdministrators')
                                      
                                      
DeleteSaveAdministratorsMenuItem()
