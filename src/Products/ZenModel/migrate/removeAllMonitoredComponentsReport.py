##############################################################################
#
# Copyright (C) Zenoss, Inc. 2022, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
This removes the All Monitored Components report since it no longer works for
large amount of devices.
"""

import logging
import Migrate

log = logging.getLogger("zen.migrate")


class RemoveAllMonitoredComponentsReport(Migrate.Step):
    version = Migrate.Version(200, 6, 0)

    def cutover(self, dmd):
        deviceReports = dmd.Reports._getOb('Device Reports', None)
        if deviceReports and deviceReports._getOb(
                'All Monitored Components', None):
            deviceReports._delObject('All Monitored Components')


RemoveAllMonitoredComponentsReport()
