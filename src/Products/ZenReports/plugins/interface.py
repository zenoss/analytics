##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.ZenReports.AliasPlugin import (
    AliasPlugin,
    Column,
    PythonColumnHandler,
    RRDColumnHandler,
)


class interface(AliasPlugin):
    """The interface usage report"""

    def getComponentPath(self):
        return "os/interfaces"

    def _getComponents(self, device, componentPath):
        components = []
        isLocal = re.compile(device.zLocalInterfaceNames)
        for i in device.os.interfaces():
            if isLocal.match(i.name()):
                continue
            if not i.monitored():
                continue
            if i.snmpIgnore():
                continue
            if not i.speed:
                continue
            components.append(i)
        return components

    def getColumns(self):
        return [
            Column("deviceName", PythonColumnHandler("device.titleOrId()")),
            Column("interface", PythonColumnHandler("component.name()")),
            Column("macAddress", PythonColumnHandler("component.macaddress")),
            Column(
                "multiIpAddress",
                PythonColumnHandler(
                    '"(multiple)" if len(component.ipaddresses()) > 1 else ""'
                ),
            ),
            Column(
                "tmp_ipAddress",
                PythonColumnHandler(
                    "component.ipaddresses()[0].id if "
                    'len(component.ipaddresses()) == 1 else ""'
                ),
            ),
            Column("interface", PythonColumnHandler("component.name()")),
            Column("speed", PythonColumnHandler("component.speed")),
            Column("input", RRDColumnHandler("inputOctets__bytes")),
            Column("output", RRDColumnHandler("outputOctets__bytes")),
            Column(
                "status",
                PythonColumnHandler(
                    '"Up" if component.getStatus()==0 else "Down"'
                ),
            ),
        ]

    def getCompositeColumns(self):
        return [
            Column(
                "ipAddress",
                PythonColumnHandler("multiIpAddress or tmp_ipAddress"),
            ),
            Column(
                "inputBits",
                PythonColumnHandler(
                    'input * 8 if input is not None else "N/A"'
                ),
            ),
            Column(
                "outputBits",
                PythonColumnHandler(
                    'output * 8 if output is not None else "N/A"'
                ),
            ),
            Column(
                "total",
                PythonColumnHandler(
                    "(input if input is not None else 0) + "
                    "(output if output is not None else 0)"
                ),
            ),
            Column(
                "totalBits",
                PythonColumnHandler(
                    "(input + output) * 8 if input is not None and "
                    'output is not None else "N/A"'
                ),
            ),
            Column(
                "percentUsed",
                PythonColumnHandler(
                    # total == total is False if total is NaN
                    "((long(total) if total == total else total) * 8)"
                    "* 100.0 / speed"
                ),
            ),
        ]
