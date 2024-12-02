##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.DataCollector.plugins.CollectorPlugin import CommandPlugin


class cpu(CommandPlugin):
    """Uses sysctl to map cpu information on CPU objects."""

    maptype = "CPUMap"
    compname = "hw"
    relname = "cpus"
    modname = "Products.ZenModel.CPU"
    command = "/usr/sbin/sysctl -a"

    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return device.os.uname == "Darwin"

    def process(self, device, results, log):
        """parse command output from this device"""
        log.info("processing processor resources %s", device.id)
        maps = []
        rm = self.relMap()

        config = {}
        for row in results.split("\n"):
            if len(row.strip()) == 0:
                continue

            values = row.split(":")
            if len(values) < 2:
                continue
            name, value = values[0:2]

            name = name.strip()
            value = value.strip()

            if name == "hw.cpufrequency":
                config["clockspeed"] = int(value)
            if name == "hw.l1icachesize":
                config["cacheSizeL1"] = int(value) / 1024
            if name == "hw.l2cachesize":
                config["cacheSizeL2"] = int(value) / 1024
            if name == "machdep.cpu.brand_string":
                config["description"] = value

        om = self.objectMap(config)
        om.setProductKey = config["description"]
        om.id = "0"
        rm.append(om)
        maps.append(rm)
        return maps
