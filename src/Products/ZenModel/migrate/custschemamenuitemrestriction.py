##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class CustomSchemaMenuRestriction(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        dmd.Devices.buildMenus({
            'More': [ 
                      {  'action': 'editCustSchema',
                         'allowed_classes': ['DeviceClass'],
                         'description': 'Custom Schema',
                         'id': 'editCustSchema',
                         'ordering': 60.0,
                         'isglobal': True,
                         'permissions': ('Change Device',)},
            ]
        })
        try:
            dmd.zenMenus.More.zenMenuItems.editCustSchema.isglobal = True
        except AttributeError: 
            pass

CustomSchemaMenuRestriction()
