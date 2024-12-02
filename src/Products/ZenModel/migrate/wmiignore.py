##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zWmiMonitorIgnore to DeviceClass.

$Id:$
'''
import Migrate

class WmiIgnore(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices._setProperty("zWmiMonitorIgnore", 
                                     False, type="boolean")

WmiIgnore()
