##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2015 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import abc
import re

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin


# vars for netstat
IFCFG_TARGET = 0
IFCFG_GATEWAY = 1
IFCFG_NETMASK = 2
IFCFG_FLAGS = 3
IFCFG_INTERFACE = 7

# vars for ip tool
# example
# default via 10.111.23.1 dev eth0
IP_GATEWAY = re.compile(r"^default via (\S+) dev (\S+)(.*)")
IP_GATEWAY_PROTO = re.compile(r"proto (\S+)")
# example: 10.111.23.0/24 dev eth0  proto kernel  scope link  src 10.111.23.72
# 10.111.23.0/24 dev eth0  proto kernel  scope link  src 10.111.23.72
#          192.168.99.0/24 dev eth0  scope link
IP_ROUTE_RECORD = re.compile(
    r"^(\S+)\s+dev\s+(\S+)\s+proto\s+(\S+)\s+scope\s+link\s+"
)
IP_ROUTE_RECORD_SHORT = re.compile(r"^(\S+)\s+dev\s+(\S+)\s+scope\s+link\s+")


class BaseParser(object):
    """Base class for command output parsers."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, plugin, log):
        self.plugin = plugin
        self.log = log

    @abc.abstractmethod
    def parse(self, results):
        """Parses command output in `results` string and returns list of
        ObjectMaps with routes information.
        """


class IpRoutesParser(BaseParser):
    """Parser class for `/usr/sbin/ip route show` command output.

    Supported format:

        default via 10.111.3.1 dev eth0
        10.111.3.0/24 dev eth0  proto kernel  scope link  src 10.111.3.244
    """

    def parse(self, results):
        """Parses command output in `results` string and returns list of
        ObjectMaps with routes information.
        """
        routes = []

        rlines = results.split("\n")
        for line in rlines:
            if "###" in line or not line:
                continue

            route = self.plugin.objectMap()
            route.id = None

            isgate = IP_GATEWAY.search(line)
            if isgate:
                # default via 10.111.23.1 dev eth0
                route.id = "0.0.0.0_0"
                route.routemask = "0"
                route.setTarget = "0.0.0.0/0"  # rfc1519
                route.setNextHopIp = isgate.group(1)
                route.setInterfaceName = isgate.group(2)
                route.routetype = "indirect"

                route.routeproto = "local"
                protomatch = IP_GATEWAY_PROTO.search(line)
                if protomatch:
                    route.routeproto = self.convertProto(protomatch.group(1))

            isroute = IP_ROUTE_RECORD.search(line)
            if isroute:
                # 192.168.99.0/24 dev eth0  scope link
                route.id = isroute.group(1).replace("/", "_")
                route.routemask = isroute.group(1).split("/", 1)[1]
                if route.routemask == "32":
                    continue
                route.setTarget = isroute.group(1)
                route.setNextHopIp = "0.0.0.0"
                route.setInterfaceName = isroute.group(2)
                route.routetype = "direct"
                route.routeproto = self.convertProto(isroute.group(3))

            isroute = IP_ROUTE_RECORD_SHORT.search(line)
            if isroute:
                route.id = isroute.group(1).replace("/", "_")
                route.routemask = isroute.group(1).split("/", 1)[1]
                if route.routemask == "32":
                    continue
                route.setTarget = isroute.group(1)
                route.setNextHopIp = "0.0.0.0"
                route.setInterfaceName = isroute.group(2)
                route.routetype = "direct"
                route.routeproto = "local"

            if route.id is not None:
                self.log.debug(
                    "Got route %s %s %s %s %s %s %s",
                    route.id,
                    route.setTarget,
                    route.routemask,
                    route.setInterfaceName,
                    route.setNextHopIp,
                    route.routetype,
                    route.routeproto,
                )
                routes.append(route)

        return routes

    def convertProto(self, routeproto):
        if routeproto.strip().lower() == "redirect":
            return "dynamic"
        return "local"


class NetstatRoutesParser(BaseParser):
    """Parser class for `/usr/bin/netstat -rn` command output.

    Supported format:

        Kernel IP routing table
        Destination  Gateway     Genmask         Flags   MSS Window  irtt Iface
        0.0.0.0      10.111.3.1  0.0.0.0         UG        0 0          0 eth0
        10.111.3.0   0.0.0.0     255.255.255.0   U         0 0          0 eth0
    """

    def parse(self, results):
        """Parses command output in `results` string and returns list of
        ObjectMaps with routes information.
        """
        routes = []

        rlines = results.splitlines()
        for line in rlines:
            fields = line.split()
            if len(fields) != 8 or not self.plugin.isip(fields[0]):
                continue

            route = self.plugin.objectMap()

            route.routemask = self.plugin.maskToBits(fields[IFCFG_NETMASK])
            if route.routemask == 32:
                continue

            if "G" in fields[IFCFG_FLAGS]:
                route.routetype = "indirect"
            else:
                route.routetype = "direct"

            if "D" in fields[IFCFG_FLAGS]:
                route.routeproto = "dynamic"
            else:
                route.routeproto = "local"

            route.id = "%s_%s" % (fields[IFCFG_TARGET], route.routemask)
            route.setTarget = "%s/%s" % (fields[IFCFG_TARGET], route.routemask)
            route.setInterfaceName = fields[IFCFG_INTERFACE]
            route.setNextHopIp = fields[IFCFG_GATEWAY]

            self.log.debug(
                "Got route %s %s %s %s %s %s %s",
                route.id,
                route.setTarget,
                route.routemask,
                route.setInterfaceName,
                route.setNextHopIp,
                route.routetype,
                route.routeproto,
            )
            routes.append(route)

        return routes


class netstat_rn(LinuxCommandPlugin):
    """
    Collect routing information using the `netstat -rn` or `ip route show`
    commands.
    """

    maptype = "RouteMap"
    command = 'export PATH=$PATH:/sbin:/usr/sbin; \
                 if which netstat >/dev/null 2>&1; then \
                     netstat -rn; \
                 elif which ip >/dev/null 2>&1; then \
                     echo "### ip addr output"; ip route show; echo "";\
                 else \
                     echo "No netstat or ip utilities were found."; exit 127; \
                 fi'
    compname = "os"
    relname = "routes"
    modname = "Products.ZenModel.IpRouteEntry"
    deviceProperties = LinuxCommandPlugin.deviceProperties + (
        "zRouteMapCollectOnlyIndirect",
    )

    def process(self, device, results, log):
        log.info(
            "Modeler %s collecting routes for device %s",
            self.name(),
            device.id,
        )
        self.log = log
        if "### ip addr" not in results:
            parser = NetstatRoutesParser(self, log)
        else:
            parser = IpRoutesParser(self, log)

        indirectOnly = getattr(device, "zRouteMapCollectOnlyIndirect", False)
        rm = self.relMap()

        for route in parser.parse(results):
            if indirectOnly and route.routetype != "indirect":
                continue

            rm.append(route)

        return rm
