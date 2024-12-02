##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from Products.ZenModel.ZenossSecurity import \
     MANAGER_ROLE, ZEN_MANAGER_ROLE, ZEN_USER_ROLE, OWNER_ROLE

class fixPropertyAccess(Migrate.Step):
    version = Migrate.Version(2, 3, 0)
    
    def cutover(self, dmd):
        dmd.manage_permission('Access contents information',
                              ['Authenticated',
                               MANAGER_ROLE,
                               ZEN_MANAGER_ROLE,
                               ZEN_USER_ROLE,
                               OWNER_ROLE],
                              0)
fixPropertyAccess()
