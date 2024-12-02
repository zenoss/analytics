##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""
Add permission for deleting devices to the ZenManager role.
"""

import Migrate
from Products.ZenModel.ZenossSecurity import *

class ZenManagerDeleteDevice(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_DELETE_DEVICE,
            [ZEN_MANAGER_ROLE, OWNER_ROLE, MANAGER_ROLE,], 1)

ZenManagerDeleteDevice()
