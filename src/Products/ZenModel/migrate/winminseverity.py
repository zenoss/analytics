##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zWinEventlogMinSeverity to DeviceClass.

'''
import Migrate

class WinMinSeverity(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWinEventlogMinSeverity"):
            dmd.Devices._setProperty("zWinEventlogMinSeverity", 2, type="int")


WinMinSeverity()
