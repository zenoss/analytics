##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds the ZenManager role.
''' 

__version__ = "$Revision$"[11:-2]


import Migrate

from Products.ZenModel.ZenossSecurity import *

class RunCommandsPermission(Migrate.Step):

    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        dmd.zport.manage_permission(ZEN_RUN_COMMANDS, 
                        [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        

RunCommandsPermission()
