##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add relations for maintenance windows and admin roles.

'''

import Migrate

class MaintenanceWindowRelations(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in ['Devices', 'Systems', 'Groups', 'Locations']:
            org = getattr(dmd, name)
            org.buildRelations()
            for org in org.getSubOrganizers():
                org.buildRelations()
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()


MaintenanceWindowRelations()
