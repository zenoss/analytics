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

class BanClassesOnAddToZenPackMenuItem(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):  
        # Build menus
        dmd.buildMenus({
        'Organizer_list': [  {  'action': 'dialog_addToZenPack',
                                # All other orgs should not be packable
                               'allowed_classes': ('DeviceClass',),
                               'description': 'Add to ZenPack...',
                               'id': 'addToZenPack',
                               'isdialog': True,
                               'ordering': 0.0,
                               'permissions': (ZEN_MANAGE_DMD,) } ],
        'More': [ {  'action': 'dialog_addOneToZenPack',
                     'allowed_classes': ['ZenPackable'],
                     'banned_classes': ('DeviceGroup',
                                        'IpNetwork',
                                        'Location',
                                        'System',
                                        'RRDDataSource',
                                        'RRDDataPoint',
                                        'ThresholdClass',
                                        'GraphDefinition',
                                        'GraphPoint'
                                        ),
                     'description': 'Add to ZenPack...',
                     'id': 'addToZenPack',
                     'isdialog': True,
                     'ordering': 1.0,
                     'permissions': (ZEN_MANAGE_DMD,) } ]
        })
        
        zm = dmd.zenMenus
        if zm.User_list.zenMenuItems._getOb('addToZenPack', False):
            zm.User_list.zenMenuItems._delObject('addToZenPack') 
        if zm.Manufacturer_list.zenMenuItems._getOb('addToZenPack', False):
            zm.Manufacturer_list.zenMenuItems._delObject('addToZenPack')
        
        for menu in dmd.zenMenus():
            for item in menu.zenMenuItems():
                if item.id == 'addToZenPack':
                    item.permissions = (ZEN_MANAGE_DMD,)

BanClassesOnAddToZenPackMenuItem()
