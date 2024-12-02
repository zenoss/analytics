##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

from Products.ZenRRD.CommandParser import CommandParser

log = logging.getLogger("zen.zencommand")

UPTIME_SENTENCE_PATTERN = re.compile(
    r"up +(?:(?:(?P<days>\d+) day\(?(?:s?)\)?(?: +)?,?(?: +)?))?"
    r"(?:(?P<hours>\d+) (?:hour(?:s?)|hr(?:s?))(?:, +)?)?"
    r"(?:(?P<minutes>\d+) (?:min(?:s?)|minute(?:s?)))?"
)

UPTIME_COLON_PATTERN = re.compile(
    r"up +(?:(?:(?P<days>\d+) day\(?(?:s?)\)?(?: +)?,?(?: +)?))?"
    r"(?:(?P<hours>\d+):(?P<minutes>\d+))"
)

UPTIME_FORMAT = "uptime: days=%(days)s, hours=%(hours)s, minutes=%(minutes)s"


def parseUptime(output):
    """
    Parse the uptime command's output capturing the days, hours and minutes
    that the system has been up. Returns a dictionary of the captured values.

    >>> UPTIME_FORMAT % parseUptime("up 12 day(s), 1:42, 1 user")
    'uptime: days=12, hours=1, minutes=42'

    >>> UPTIME_FORMAT % parseUptime("up 1 day, 1:42, 1 user")
    'uptime: days=1, hours=1, minutes=42'

    >>> UPTIME_FORMAT % parseUptime("up 5 days, 1:42, 1 user")
    'uptime: days=5, hours=1, minutes=42'

    >>> UPTIME_FORMAT % parseUptime("up 3 days, 6 min, 1 user")
    'uptime: days=3, hours=0, minutes=6'

    >>> UPTIME_FORMAT % parseUptime("up 3 days, 2 hours, 6 min, 1 user")
    'uptime: days=3, hours=2, minutes=6'

    >>> UPTIME_FORMAT % parseUptime("up 1:14, 1 user")
    'uptime: days=0, hours=1, minutes=14'

    >>> UPTIME_FORMAT % parseUptime("up 4 min, 1 user")
    'uptime: days=0, hours=0, minutes=4'

    >>> UPTIME_FORMAT % parseUptime("up 8 hrs, 1 user")
    'uptime: days=0, hours=8, minutes=0'

    >>> UPTIME_FORMAT % parseUptime("up 2 days, 8 hrs, 1 user")
    'uptime: days=2, hours=8, minutes=0'
    """

    if re.search(r"\d+:\d+, +\d+ user", output):
        match = UPTIME_COLON_PATTERN.search(output)
    else:
        match = UPTIME_SENTENCE_PATTERN.search(output)

    if match:
        uptime = dict((k, int(v)) for k, v in match.groupdict(0).items())
        log.debug(UPTIME_FORMAT, uptime)
    else:
        uptime = None
        log.debug("uptime: no match")

    return uptime


def asTimeticks(days=0, hours=0, minutes=0):
    return ((days * 24 + hours) * 60 + minutes) * 60 * 100


def parseSysUpTime(output):
    """
    Parse the sysUpTime (measured in timeticks) from the output of the uptime
    command.
    """
    uptime = parseUptime(output)

    if uptime:
        sysUpTime = asTimeticks(**uptime)
    else:
        sysUpTime = None

    return sysUpTime


class uptime(CommandParser):
    def processResults(self, cmd, result):
        """
        Parse the results of the uptime command to get sysUptime and load
        averages.
        """
        output = cmd.result.output

        dps = dict((dp.id, dp) for dp in cmd.points)

        if "sysUpTime" in dps:
            sysUpTime = parseSysUpTime(output)
            if sysUpTime:
                result.values.append((dps["sysUpTime"], sysUpTime))

        match = re.search(
            r" load averages?: " r"([0-9.]+),? ([0-9.]+),? ([0-9.]+).*$",
            output,
        )
        if match:
            for i, dp in enumerate(
                ("laLoadInt1", "laLoadInt5", "laLoadInt15")
            ):
                if dp in dps:
                    result.values.append((dps[dp], float(match.group(i + 1))))
        return result
