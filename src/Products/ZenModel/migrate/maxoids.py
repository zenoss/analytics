##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add zMaxOIDPerRequest to DeviceClass.

$Id:$
'''
import Migrate

class MaxOIDPerRequest(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zMaxOIDPerRequest"):
            dmd.Devices._setProperty("zMaxOIDPerRequest", 40)

MaxOIDPerRequest()
