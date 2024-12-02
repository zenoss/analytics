##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenModel.ZenossSecurity import ZEN_MANAGER_ROLE, MANAGE_TRIGGER, UPDATE_TRIGGER, UPDATE_NOTIFICATION, MANAGE_NOTIFICATION_SUBSCRIPTIONS

__doc__ = '''
This migration script adds the Manage Trigger permission to the ZenManager role.
'''

import Migrate


class AddTriggerPermToZenManager(Migrate.Step):
    version = Migrate.Version(200, 0, 0)

    def addPermissions(self, obj, permission, roles=None, acquire=0):
        if not roles:
            roles = []
        if not permission in obj.possible_permissions():
            obj.__ac_permissions__ = (
                obj.__ac_permissions__ + ((permission, (), roles),))

        for permissionDir in obj.rolesOfPermission(permission):
            if permissionDir['selected']:
                if permissionDir['name'] not in roles:
                    roles.append(permissionDir['name'])
        obj.manage_permission(permission, roles, acquire)

    def cutover(self, dmd):
        zport = dmd.zport
        self.addPermissions(zport, MANAGE_TRIGGER, [ZEN_MANAGER_ROLE], 1)
        self.addPermissions(zport, UPDATE_TRIGGER, [ZEN_MANAGER_ROLE], 1)
        self.addPermissions(zport, UPDATE_NOTIFICATION, [ZEN_MANAGER_ROLE], 1)
        self.addPermissions(zport, MANAGE_NOTIFICATION_SUBSCRIPTIONS, [ZEN_MANAGER_ROLE], 1)


AddTriggerPermToZenManager()
