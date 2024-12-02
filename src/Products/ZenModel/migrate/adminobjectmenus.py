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

class AdminObjectMenus(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):

        dmd.buildMenus(
            {'AdministeredObjects_list': [{
               'action': 'dialog_addAdministeredDevice',
                'description': 'Add Device...',
                'id': 'addAdministeredDevice',
                'isdialog': True,
                'ordering': 90.5,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredDeviceClass',
                'description': 'Add Device Class...',
                'id': 'addAdministeredDeviceClass',
                'isdialog': True,
                'ordering': 90.4,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredSystem',
                'description': 'Add System...',
                'id': 'addAdministeredSystem',
                'isdialog': True,
                'ordering': 90.3,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredGroup',
                'description': 'Add Group...',
                'id': 'addAdministeredGroup',
                'isdialog': True,
                'ordering': 90.2,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredLocation',
                'description': 'Add Location...',
                'id': 'addAdministeredLocation',
                'isdialog': True,
                'ordering': 90.1,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_deleteAdministeredObjects',
                'description': 'Delete Admin Objects...',
                'id': 'deleteAdministeredObjects',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            }],
            'UserSettings': [{ 'action': 'dialog_saveUserSettings',
                'description': 'Save User Settings...',
                'id': 'saveUserSettings',
                'isdialog': True,
                'ordering': 0.0,
                'permissions': (ZEN_CHANGE_SETTINGS,)
            }],
            'ActionRule_list': [  {  'action': 'dialog_addActionRule',
                'description': 'Add Alerting Rule...',
                'id': 'addActionRule',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)},
            {  'action': 'dialog_deleteActionRules',
                'description': 'Delete Rules...',
                'id': 'deleteActionRules',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)}],
           'ActionRuleWindow_list': [  {  'action': 'dialog_addActionRuleWindow',
                'description': 'Add Rule Window...',
                'id': 'addActionRuleWindow',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)},
           {  'action': 'dialog_deleteActionRuleWindows',
                'description': 'Delete Rule Windows...',
                'id': 'deleteActionRuleWindows',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)}],
           'EventView_list': [  {  'action': 'dialog_addEventView',
                'description': 'Add Event View...',
                'id': 'addEventView',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_EVENT_VIEWS,)},
           {  'action': 'dialog_deleteEventViews',
                'description': 'Delete Event Views...',
                'id': 'deleteEventViews',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_EVENT_VIEWS,)}],
        })
        if hasattr(dmd.zenMenus.AdministeredObjects_list.zenMenuItems,
            'saveAdministeredObjects'):
            dmd.zenMenus.AdministeredObjects_list.manage_deleteZenMenuItem(
                'saveAdministeredObjects')


AdminObjectMenus()
