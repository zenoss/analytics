##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenReports import Utils
from Products.ZenReports.AliasPlugin import (
    AliasPlugin,
    Column,
    PythonColumnHandler,
    RRDColumnHandler,
)


def _getAvailableReal(availableBytes, bufferedBytes, cachedBytes):
    if availableBytes is None:
        return None
    elif bufferedBytes is None or cachedBytes is None:
        return availableBytes
    else:
        return availableBytes + bufferedBytes + cachedBytes


def _getPercentUtilization(availableReal, totalReal, usedPercent):
    if usedPercent:
        return usedPercent
    elif totalReal and availableReal:
        return Utils.percent(totalReal - availableReal, totalReal)
    else:
        return None


class memory(AliasPlugin):
    "The memory usage report"

    def getColumns(self):
        return [
            Column("deviceName", PythonColumnHandler("device.titleOrId()")),
            Column("device_url", PythonColumnHandler("device.getDeviceUrl()")),
            Column("totalReal", PythonColumnHandler("device.hw.totalMemory")),
            Column(
                "availableReal_tmp", RRDColumnHandler("memoryAvailable__bytes")
            ),
            Column("buffered", RRDColumnHandler("memoryBuffered__bytes")),
            Column("cached", RRDColumnHandler("memoryCached__bytes")),
            Column("usedPercent_tmp", RRDColumnHandler("memoryUsed__pct")),
        ]

    def getCompositeColumns(self):
        return [
            Column(
                "availableReal",
                PythonColumnHandler(
                    "getAvailableReal( availableReal_tmp, buffered, cached )",
                    dict(getAvailableReal=_getAvailableReal),
                ),
            ),
            Column(
                "percentUsed",
                PythonColumnHandler(
                    "getPercentUtilization("
                    "availableReal,totalReal,usedPercent_tmp)",
                    dict(getPercentUtilization=_getPercentUtilization),
                ),
            ),
        ]
