##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class MonitoringMenuItem(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        dmd.buildMenus({  
            'IpService': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'WinService': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'FileSystem': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'IpInterface': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
            'OSProcess': [
                     {  'action': 'dialog_changeMonitoring',
                        'isdialog': True,
                        'description': 'Monitoring...',
                        'id': 'changeMonitoring',
                        'ordering': 0.0,
                        'permissions': ('Manage DMD',)},
                     ],
        })

MonitoringMenuItem()
