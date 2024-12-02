##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from Products.ZenModel.ZenossSecurity import *

class MoveHistoryToMoreMenu(Migrate.Step):
    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        # Build menus
        dmd.buildMenus({
        'More': [ {  'action': 'viewHistoryEvents',
                     'allowed_classes': ['EventClass', 'EventClassInst', 
                        'Device', 'DeviceOrganizer', 'Location', 'System',
                        'DeviceClass'],
                     'banned_classes' : ['IpNetwork'],
                     'description': 'Event History',
                     'id': 'historyEvents',
                     'ordering': 1.0,
                     'permissions': (ZEN_VIEW,) } ]
        })
        viewHistory = dmd.zenMenus.More.zenMenuItems.viewHistory
        if not viewHistory.banned_classes:
            viewHistory.banned_classes = ('IpNetwork',)


MoveHistoryToMoreMenu()
