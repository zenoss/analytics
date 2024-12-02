##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Delete the previous CPU Util, FS Util and All Monitored Components reports.  
The slightly modified ones will get loaded at the end of migration.

$Id:$
'''
import Migrate

class RemoveOldCpuFsAndComponentsReports(Migrate.Step):
    version = Migrate.Version(3,0,0)

    def cutover(self, dmd):
        if hasattr(dmd.Reports, 'Performance Reports'):
            perfReports = dmd.Reports['Performance Reports']

            if hasattr(perfReports, 'CPU Utilization'):
                perfReports._delObject('CPU Utilization')
            if hasattr(perfReports, 'Filesystem Util Report'):
                perfReports._delObject('Filesystem Util Report')

        if hasattr(dmd.Reports, 'Device Reports'):
            devReports = dmd.Reports['Device Reports']

            if hasattr(devReports, 'All Monitored Components'):
                devReports._delObject('All Monitored Components')

RemoveOldCpuFsAndComponentsReports()
