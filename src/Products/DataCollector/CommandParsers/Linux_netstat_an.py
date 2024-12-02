##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .CommandParser import CommandParser


class Linux_netstat_an(CommandParser):
    """
    Parses output of 'netstat' command.
    """

    command = "netstat -ln | grep 0.0.0.0:*"

    def condition(self, device, log):
        pp = device.getPrimaryPath()
        return "Linux" in pp

    def parse(self, device, results, log):
        log.info("Collecting Ip Services for device %s", device.id)
        rm = self.newRelationshipMap("ipservices")
        rlines = results.split("\n")
        services = {}
        # normalize on address 0.0.0.0 means all addresses
        for line in rlines:
            aline = line.split()
            if len(aline) < 5:
                continue
            try:
                proto = aline[0]
                addr, port = aline[3].split(":")
                if int(port) > 1024:
                    continue  # FIXME
                if addr == "0.0.0.0" or port not in services:
                    services[port] = (addr, proto)
            except ValueError:
                log.exception("failed to parse ipservice information")
        for port, value in services.items():
            addr, proto = value
            om = self.newObjectMap("ZenModel.IpService")
            om["id"] = "-".join((addr, proto, port))
            om["ipaddress"] = addr
            om["setPort"] = port
            om["setProtocol"] = proto
            om["discoveryAgent"] = "IpServiceMap"
            rm.append(om)
            log.debug("Adding TCP Service %s %s", addr, port)
        return rm

    def description(self):
        return "run netstat -ln on server to build ipservices"
