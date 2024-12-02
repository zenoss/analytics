##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.PluggableAuthService import plugins
from Products.ZenModel.ZenossSecurity import *   

class AddGroupManager(Migrate.Step):
    
    version = Migrate.Version(2, 1, 0)
   
    def cutover(self, dmd):
        
        dmd.buildMenus(
            {'Group_list': [
               {  'action': 'dialog_addUserGroup',
                  'description': 'Add New Group...',
                  'id': 'addUserGroup',
                  'isdialog': True,
                  'ordering': 90.1,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_deleteUserGroups',
                  'description': 'Delete Groups...',
                  'id': 'deleteUserGroups',
                  'isdialog': True,
                  'ordering': 90.0,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_addUserToGroup',
                  'description': 'Add User...',
                  'id': 'addUserToGroups',
                  'isdialog': True,
                  'ordering': 80.1,
                  'permissions': (ZEN_MANAGE_DMD,)} ],
              'GroupUser_list': [
               {  'action': 'dialog_addUserToAGroup',
                  'description': 'Add User...',
                  'id': 'addUserToAGroup',
                  'isdialog': True,
                  'ordering': 80.1,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_deleteUsersFromGroup',
                  'description': 'Delete Users...',
                  'id': 'deleteUsersFromGroup',
                  'isdialog': True,
                  'ordering': 80.0,
                  'permissions': (ZEN_MANAGE_DMD,)} ]
        })
        if hasattr(dmd.zenMenus.Group_list.zenMenuItems, 
            'addUserToGroup'):
            dmd.zenMenus.Group_list.manage_deleteZenMenuItem(
                'addUserToGroup')
        if hasattr(dmd.zenMenus.Group_list.zenMenuItems, 
            'deleteUsersFromGroup'):
            dmd.zenMenus.Group_list.manage_deleteZenMenuItem(
                'deleteUsersFromGroup')
        if hasattr(dmd.zenMenus.GroupUser_list.zenMenuItems, 
            'addUserToGroup'):
            dmd.zenMenus.GroupUser_list.manage_deleteZenMenuItem(
                'addUserToGroup')
        self._addGroupManager(dmd.zport)


    GROUP_ID = 'groupManager'

    def _addGroupManager(self, zport):
        acl = zport.acl_users
        if not hasattr(acl, self.GROUP_ID):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, self.GROUP_ID)
        acl.groupManager.manage_activateInterfaces(['IGroupsPlugin',])


AddGroupManager()
