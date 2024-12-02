##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenReports.AliasPlugin import (
    AliasPlugin,
    Column,
    PythonColumnHandler,
    RRDColumnHandler,
)


class cpu(AliasPlugin):
    """
    The cpu usage report
    """

    def getColumns(self):
        # alias/dp id : column name
        return [
            Column("deviceName", PythonColumnHandler("device.titleOrId()")),
            Column("laLoadInt5", RRDColumnHandler("loadAverage5min")),
            Column("cpuPercent", RRDColumnHandler("cpu__pct")),
        ]
