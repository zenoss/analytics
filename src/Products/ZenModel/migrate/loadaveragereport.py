##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Delete the non-working load average report.  Reports will be added back in 1.1.

$Id:$
'''
import Migrate

class LoadAverageReport(Migrate.Step):
    version = Migrate.Version(1,0,0)

    def cutover(self, dmd):
        if hasattr(dmd.Reports, 'Performance Reports'):
            dmd.Reports._delObject("Performance Reports")

LoadAverageReport()
