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


class CiscoShowHardware(CommandParser):
    """
    Parses the show hardware command and returns CPU type and total memory.
    """

    command = "show hardware"

    def condition(self, device, log):
        return device.hw.getManufacturerName() == "Cisco"

    def parse(self, device, results, log):
        cpumem = re.compile(r"\((.+)\) processor .* ([\d\/K]+) bytes").search
        om = self.newObjectMap()
        for line in results.split("\n"):
            m = cpumem(line)
            if m:
                om["cpuType"] = m.group(1)
                mems = m.group(2)
                if mems.find("/") > -1:
                    mems = mems.split("/")
                else:
                    mems = (mems,)
                tmem = 0.0
                for mem in mems:
                    if mem[-1] == "K":
                        mem = float(mem[:-1])
                    tmem += mem
                tmem /= 1024.0
                om["totalMemory"] = round(tmem)
        return om

    def description(self):
        return (
            "Get the CPUType and Total Memory from the show hardware command"
        )
