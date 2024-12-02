##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This removes the Aggregate Reports report since it no longer works in Europa.
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")

class RemoveAggregateReport(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        performanceReports = dmd.Reports._getOb('Performance Reports', None)
        if performanceReports and performanceReports._getOb('Aggregate Reports', None):
            performanceReports._delObject('Aggregate Reports')
RemoveAggregateReport()
