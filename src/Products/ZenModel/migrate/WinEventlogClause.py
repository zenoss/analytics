##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """ Add zWinEventlogClause to DeviceClass.

Allows queries based of the Windows Event Log rather than just the severity.
"""

import Migrate

class WinEventlogClause(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWinEventlogClause"):
            dmd.Devices._setProperty("zWinEventlogClause", '', type="string")

WinEventlogClause()
