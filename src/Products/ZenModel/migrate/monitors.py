##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


'Add/subtract monitors'

import Migrate

class Monitors(Migrate.Step):
    "Set the sub_class value on the usual Monitor objects"
    version = Migrate.Version(1, 0, 0)

    def cutover(self, dmd):
        dmd.Monitors.sub_class = 'MonitorClass'
        dmd.Monitors.Performance.sub_class = 'PerformanceConf'
        dmd.Monitors.StatusMonitors.sub_class = 'StatusMonitorConf'

Monitors()
