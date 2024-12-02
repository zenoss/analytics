##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class AddEventMenuItem(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'Event_list': [
                     {  'action': 'dialog_addEvent',
                        'isdialog': True,
                        'allowed_classes': ('EventClass',),
                        'description': 'Add Event...',
                        'id': 'addEventList',
                        'ordering': 80.0,
                        'permissions': ('Manage DMD',)},
                     ]})

AddEventMenuItem()
