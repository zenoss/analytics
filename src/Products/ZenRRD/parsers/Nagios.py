##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Nagios

Uses the Nagios API defintions from
http://nagios.sourceforge.net/docs/3_0/pluginapi.html and from
http://nagiosplug.sourceforge.net/developer-guidelines.html#PLUGOUTPUT
"""

import re

from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.Utils import getExitMessage

# Performance datapoints syntax
# Matches substrings having the form <key>=<value> with optional trailing
# whitespace.  E.g. if this is the perf data:
#
#     rta=0.337000ms;180.000000;300.000000;0.000000 pl=0%;100;100;0.
#
# this is the output (using findall()):
#
# [('rta=0.337000ms;180.000000;300.000000;0.000000', 'rta', '', '0.337000'),
#  ('pl=0%;100;100;0', 'pl', '', '0')]
#
perfParser = re.compile(r"""(([^ =']+|'([^']+)')=([-0-9.eE]+)\S*)""")


class _BadData(Exception):
    """
    Raised by splitMultLine when plugin output is not parseable.
    """


class Nagios(CommandParser):
    @staticmethod
    def splitMultiLine(output):
        """
        Convert the plugin output into component parts:
             summary, performance_data
        """
        output = output.strip()
        text, perf = [], []
        if not output:
            raise Exception("No output from COMMAND plugin")

        # Expected format is (assuming performance data):
        #
        #    <text>|<perf data>
        #    <extra text>
        #    <extra text>|<extra perf data>
        #    <extra perf data>
        #
        # The first line has text and, optionally, perf data.  Subsequent
        # lines will have the format of <text>|<perf> across multiple lines.
        lines = output.splitlines()
        firstLine = lines[0].strip()
        additionalLines = " ".join(lines[1:])
        text, perf = [], []
        # Extract text and data from first line
        segments = firstLine.split("|")
        # If there are any segments, the first segment is text.
        if segments:
            text.append(segments.pop(0))
        # Extract additional text (due to bad pipe usage)
        while len(segments) > 1:
            text.append(segments.pop(0))
        # Extract the perf data (if exists)
        if segments:
            perf.append(segments.pop(0))
        # Now extract any additional data that may exist.
        if additionalLines:
            # Split text and perf data apart
            segments = additionalLines.split("|")
            # Extract text data (if any)
            if segments:
                text.extend(segments.pop(0).splitlines())
            # Extract perf data (if any)
            if segments:
                perf.extend(segments.pop(0).splitlines())

        return text, perf

    def processPerfData(self, rawPerfData):
        """
        Create a dictionary of datapoint:value entries from
        the plugin output.
        This funtion removes a ' (represented as '' in the label)
        from the label.  There's just too much opportunity to mess
        something up by keeping a shell meta-character.
        """
        perfData = {}
        all_data = " ".join(rawPerfData)
        # Strip out all '' strings
        all_data = all_data.replace("''", "")

        for _, label, quote_label, value in perfParser.findall(all_data):
            if quote_label:
                label = quote_label
            try:
                value = float(value.strip())
            except Exception:
                value = "U"
            perfData[label] = value

        return perfData

    def processResults(self, cmd, result):
        output = cmd.result.output
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        if exitCode == 0:
            severity = 0
        elif exitCode == 2:
            severity = min(severity + 1, 5)

        evt = {
            "device": cmd.deviceConfig.device,
            "message": output,
            "severity": severity,
            "component": cmd.component,
            "eventKey": cmd.eventKey,
            "eventClass": cmd.eventClass,
        }
        try:
            summary, rawPerfData = self.splitMultiLine(output)
        except Exception as ex:
            evt.update(
                {
                    "error_codes": "Datasource: %s - Code: %s - Msg: %s"
                    % (cmd.name, exitCode, getExitMessage(exitCode)),
                    "performanceData": None,
                    "summary": str(ex),
                }
            )
        else:
            evt.update(
                {
                    "performanceData": rawPerfData,
                    "summary": summary[0],
                    "message": "\n".join(summary),
                }
            )
            perfData = self.processPerfData(rawPerfData)
            for dp in cmd.points:
                if dp.id in perfData:
                    result.values.append((dp, perfData[dp.id]))
        result.events.append(evt)
