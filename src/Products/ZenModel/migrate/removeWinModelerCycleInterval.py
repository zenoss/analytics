##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class RemoveWinModelerCycleInterval(Migrate.Step):
    ATTR_NAME = 'winmodelerCycleInterval'
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        for name in dmd.Monitors.getPerformanceMonitorNames():
            monitor = dmd.Monitors.getPerformanceMonitor(name)
            if hasattr(monitor, RemoveWinModelerCycleInterval.ATTR_NAME):
                delattr(monitor, RemoveWinModelerCycleInterval.ATTR_NAME)

RemoveWinModelerCycleInterval()
