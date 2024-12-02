##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """ChangeSnmpDefaults

Change zSnmpVer, zSnmpTries and zSnmpTimeout
"""

import Migrate

class ChangeSnmpDefaults(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):

        # only update the props if they are still the defaults
        if dmd.Devices.zSnmpVer == 'v1':
            dmd.Devices._updateProperty('zSnmpVer', 'v2c')
        if dmd.Devices.zSnmpTries == 2:
            dmd.Devices._updateProperty('zSnmpTries', 6)
        if dmd.Devices.zSnmpTimeout == 2.5:
            dmd.Devices._updateProperty('zSnmpTimeout', 1)

ChangeSnmpDefaults()
