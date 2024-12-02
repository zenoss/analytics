##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class StatusMonitorMenus(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):
        
        # Build menus
        dmd.buildMenus({  
            'PerformanceMonitor_list': [
                {  'action': 'performanceTemplates',
                   'description': 'Templates',
                   'id': 'performanceTemplates',
                   'ordering': 16.0,
                   'permissions': ('View Device',),
                }],
            'StatusMonitor_list': [
                {  'action': 'performanceTemplates',
                   'description': 'Templates',
                   'id': 'performanceTemplates',
                   'ordering': 16.0,
                   'permissions': ('View Device',),
                }],
        })


StatusMonitorMenus()
