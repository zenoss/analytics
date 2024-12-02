##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class DiscoverNetworkMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'TopLevel': [
                     {  'action': 'discoverNetwork',
                        'allowed_classes': ('IpNetwork',),
                        'banned_ids': ('Networks',),
                        'description': 'Discover Devices',
                        'id': 'discoverMyNetwork',
                        'isdialog': False,
                        'ordering': 80.0,
                        'permissions': ('Manage DMD',)}]})

DiscoverNetworkMenuItem()
