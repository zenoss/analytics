##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script removes ZEN_DEFINE_COMMANDS_EDIT permission
from the ZenManager role.
''' 

__version__ = "$Revision$"[11:-2]


import Migrate

from Products.ZenModel.ZenossSecurity import *

class RemoveCommandsEditPermission(Migrate.Step):

    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_DEFINE_COMMANDS_EDIT,
            [MANAGER_ROLE], 1)

RemoveCommandsEditPermission()
