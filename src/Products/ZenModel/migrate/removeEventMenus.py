##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class RemoveEventMenus(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        zenMenus = dmd.zenMenus

        # Remove menu items
        topLevel = zenMenus.TopLevel
        removeItems(topLevel, 'addEvent', 'manage_clearCache', 'manage_clearHeartbeats', 'manage_refreshConversions')

        # Remove menus
        removeMenus(dmd.zenMenus, 'ActionRuleWindow_list', 'ActionRule_list', 'EventView_list', 'Event_list',
                    'HistoryEvent_list')


def removeItems(menu, *items):
    for item in items:
        if hasattr(menu.zenMenuItems, item):
            menu.zenMenuItems._delObject(item)

def removeMenus(zenMenus, *menus):
    for menu in menus:
        if hasattr(zenMenus, menu):
            zenMenus._delObject(menu)

RemoveEventMenus()
