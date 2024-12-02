##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
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

class ZenManagerRole(Migrate.Step):

    version = Migrate.Version(2, 4, 0)
    
    def addPermissions(self, obj, permission, roles=None, acquire=0):
        if not roles:
            roles = []
        if not permission in obj.possible_permissions():
            obj.__ac_permissions__=(
                obj.__ac_permissions__+((permission,(),roles),))
            
        for permissionDir in obj.rolesOfPermission(permission):
            if permissionDir['selected']:
                if permissionDir['name'] not in roles:
                    roles.append(permissionDir['name'])
        obj.manage_permission(permission, roles, acquire)
            
            
    def cutover(self, dmd):
        zport = dmd.zport
        if not ZEN_MANAGER_ROLE in zport.__ac_roles__:
            zport.__ac_roles__ += (ZEN_MANAGER_ROLE,)
        rms = (dmd.getPhysicalRoot().acl_users.roleManager,
                    zport.acl_users.roleManager)
        for rm in rms:
            if not ZEN_MANAGER_ROLE in rm.listRoleIds():
                rm.addRole(ZEN_MANAGER_ROLE)
        
        self.addPermissions(zport, ZEN_CHANGE_DEVICE, 
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_MANAGE_DMD, 
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_DELETE, 
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_ADD, 
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_VIEW, 
            [ZEN_USER_ROLE,ZEN_MANAGER_ROLE,MANAGER_ROLE,OWNER_ROLE])
        self.addPermissions(zport, ZEN_MANAGE_EVENTMANAGER,
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_MANAGE_EVENTS,
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_SEND_EVENTS,
            [ZEN_MANAGER_ROLE, OWNER_ROLE,MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_VIEW_HISTORY, 
            [ZEN_USER_ROLE, ZEN_MANAGER_ROLE, MANAGER_ROLE,], 1)
        self.addPermissions(zport, ZEN_COMMON,
            ["Authenticated", ZEN_USER_ROLE, ZEN_MANAGER_ROLE, 
                MANAGER_ROLE, OWNER_ROLE], 1)
        self.addPermissions(zport, ZEN_CHANGE_SETTINGS, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1)
        self.addPermissions(zport, ZEN_CHANGE_ALERTING_RULES, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE, OWNER_ROLE], 1) 
        self.addPermissions(zport, ZEN_CHANGE_ADMIN_OBJECTS, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_CHANGE_EVENT_VIEWS, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_ADMIN_DEVICE, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_MANAGE_DEVICE, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_ZPROPERTIES_EDIT, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_ZPROPERTIES_VIEW, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_EDIT_LOCAL_TEMPLATES, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_DEFINE_COMMANDS_EDIT, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_DEFINE_COMMANDS_VIEW, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)  
        self.addPermissions(zport, ZEN_MAINTENANCE_WINDOW_EDIT, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_MAINTENANCE_WINDOW_VIEW, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_ADMINISTRATORS_EDIT, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        self.addPermissions(zport, ZEN_ADMINISTRATORS_VIEW, 
            [ZEN_MANAGER_ROLE, MANAGER_ROLE], 1)
        

ZenManagerRole()
