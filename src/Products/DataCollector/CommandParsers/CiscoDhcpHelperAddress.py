##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from .CommandParser import CommandParser


class CiscoDhcpHelperAddress(CommandParser):
    """
    Parses the output of a command to return a datamap.
    """

    command = "show run | include helper-address"

    def condition(self, device, log):
        return "UBR" in device.getPrimaryPath()

    def parse(self, device, results, log):
        dhcpips = {}
        findip = re.compile(r"(\d+\.\d+\.\d+\.\d+)$").search
        for line in results.split("\n"):
            m = findip(line)
            if m:
                ip = m.group(1)
                dhcpips[ip] = 1
        om = self.newObjectMap()
        om["setDhcpHelpers"] = dhcpips.keys()
        return om

    def description(self):
        return "Collect dhcp helper servers that a UBR uses"
