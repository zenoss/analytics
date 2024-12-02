##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


from Products.ZenModel.MaintenanceWindow import createMaintenanceWindowCatalog

import logging
log = logging.getLogger("zen.migrate")

class MaintenanceWindowCatalog(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        if not hasattr(dmd, 'maintenanceWindowSearch'):
            createMaintenanceWindowCatalog(dmd)
            # Indexing is done by the twotwoindexing step

maintwindowcatalog = MaintenanceWindowCatalog()
