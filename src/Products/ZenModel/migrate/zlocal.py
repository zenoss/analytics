##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zLocalIpAddresses and zLocalInterfaceNames to DeviceClass.

$Id:$
'''
import Migrate

class ZLocalIps(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zLocalIpAddresses"):
            dmd.Devices._setProperty("zLocalIpAddresses", 
                '^127|^0\.0|^169\.254|^224')
        if not dmd.Devices.hasProperty("zLocalInterfaceNames"):
            dmd.Devices._setProperty("zLocalInterfaceNames", '^lo|^vmnet')

ZLocalIps()
