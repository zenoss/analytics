##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zHardDiskMapMatch to DeviceClass.

'''
import Migrate

class zHardDiskMapMatch(Migrate.Step):
    version = Migrate.Version(2, 3, 0)
    
    def cutover(self, dmd):
        if dmd.Devices.hasProperty('zHardDiskMapMatch'):
            return

        dmd.Devices._setProperty('zHardDiskMapMatch',
                '', 'string', 'Regex that disks must match to be modeled', True)

        try:
            if not dmd.Devices.Server.Windows.hasProperty('zHardDiskMapMatch'):
                dmd.Devices.Server.Windows._setProperty('zHardDiskMapMatch', '.*')
        except AttributeError:
            pass

        try:
            if not dmd.Devices.Server.Linux.hasProperty('zHardDiskMapMatch'):
                dmd.Devices.Server.Linux._setProperty('zHardDiskMapMatch',
                                                      '^[hs]d[a-z]\d+$|c\d+t\d+d\d+s\d+$|^cciss\/c\dd\dp\d$|' \
                                                      '^dm\-\d$')
        except AttributeError:
            pass

zHardDiskMapMatch()
