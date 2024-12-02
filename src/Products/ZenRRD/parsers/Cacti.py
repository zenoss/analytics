##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.Utils import getExitMessage

# how to parse each value from a Cacti plugin
CacParser = re.compile(
    r"""([^ :']+|'(.*)'+)\s*:\s*([-+]?[-0-9.]+(?:[Ee][-+]?\d+)?)"""
)


class Cacti(CommandParser):
    def processResults(self, cmd, result):
        output = cmd.result.output
        output = output.split("\n")[0].strip()
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        if output.find("|") >= 0:
            msg, values = output.split("|", 1)
            msg, values = output, ""

        elif CacParser.search(output):
            msg, values = "", output

        elif len(cmd.points) == 1:
            # Special case for plugins that only return one datapoint
            try:
                number = float(output)
                result.values.append((cmd.points[0], number))
                msg, values = "", output
            except Exception:
                msg, values = output, ""

        else:
            msg, values = output, ""

        msg = msg.strip() or "Datasource: %s - Code: %s - Msg: %s" % (
            cmd.name,
            exitCode,
            getExitMessage(exitCode),
        )
        if exitCode != 0:
            if exitCode == 2:
                severity = min(severity + 1, 5)
            result.events.append(
                dict(
                    device=cmd.deviceConfig.device,
                    summary=msg,
                    severity=severity,
                    message=msg,
                    performanceData=values,
                    eventKey=cmd.eventKey,
                    eventClass=cmd.eventClass,
                    component=cmd.component,
                )
            )

        for parts in CacParser.findall(values):
            label = parts[0].replace("''", "'")
            try:
                value = float(parts[2])
            except Exception:
                value = "U"
            for dp in cmd.points:
                if dp.id == label:
                    result.values.append((dp, value))
                    break
