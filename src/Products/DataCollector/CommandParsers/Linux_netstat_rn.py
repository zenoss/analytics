##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.ZenUtils.IpUtil import isip, maskToBits

from .CommandParser import CommandParser

_TARGET = 0
_GATEWAY = 1
_NETMASK = 2
_FLAGS = 3
_INTERFACE = 7


class Linux_netstat_rn(CommandParser):
    """
    Parses output of 'netstat' command.
    """

    command = "netstat -rn"
    componentName = "os"

    def condition(self, device, log):
        osver = device.os.getProductName()
        return osver.find("Linux") > -1

    def parse(self, device, results, log):
        log.info("Collecting routes for device %s", device.id)
        indirectOnly = getattr(device, "zRouteMapCollectOnlyIndirect", False)
        rm = self.newRelationshipMap("routes", "os")
        rlines = results.split("\n")
        for line in rlines:
            aline = line.split()
            if len(aline) != 8 or not isip(aline[0]):
                continue
            route = self.newObjectMap("Products.ZenModel.IpRouteEntry")

            route["routemask"] = maskToBits(aline[_NETMASK])
            if route["routemask"] == 32:
                continue

            if "G" in aline[_FLAGS]:
                route["routetype"] = "indirect"
            else:
                route["routetype"] = "direct"
            if indirectOnly and route["routetype"] != "indirect":
                continue

            route["id"] = aline[_TARGET]
            route["setTarget"] = route["id"] + "/" + str(route["routemask"])
            route["id"] = route["id"] + "_" + str(route["routemask"])
            route["setInterfaceName"] = aline[_INTERFACE]
            route["setNextHopIp"] = aline[_GATEWAY]
            rm.append(route)
        return rm

    def description(self):
        return "run netstat -an on server to build ipservices"
