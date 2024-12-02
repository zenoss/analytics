##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import abc

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin
from Products.ZenUtils import IpUtil


class BaseParser(object):
    """Base class for command output parsers."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, log):
        self.log = log

    @abc.abstractmethod
    def parse(self, results):
        """Parses command output in `results` string and returns services
        information in format:

            [(proto, port, addr), ...]
        """


class SsServicesParser(BaseParser):
    """Parser class for `/usr/sbin/ss -lntu` command output.

    Supported format:

        Netid State      Recv-Q Send-Q  Local Address:Port   Peer Address:Port
        tcp   UNCONN     0      0                   *:68                *:*
        tcp   UNCONN     0      0           127.0.0.1:323               *:*
        tcp   UNCONN     0      0                  :::38496            :::*
        tcp   UNCONN     0      0                  :::111              :::*
        tcp   LISTEN     0      128                 *:111               *:*
        tcp   LISTEN     0      128                 *:22                *:*
        tcp   LISTEN     0      100         127.0.0.1:25                *:*
        tcp   LISTEN     0      128                :::111              :::*
        tcp   LISTEN     0      128                :::22               :::*
        tcp   LISTEN     0      100               ::1:25               :::*
    """

    def parse(self, results):
        """Parses command output in `results` string and returns services
        information in format:

            [(proto, port, addr), ...]
        """
        services = []

        for line in results.split("\n"):
            # tcp    UNCONN     0      0      *:68      *:*
            fields = line.split()
            if len(fields) != 6:
                continue
            try:
                proto = fields[0]
                # please note protocol alway be tcp due a bug in RH;
                # see https://bugzilla.redhat.com/show_bug.cgi?id=1063927
                if fields[1] == "UNCONN":
                    proto = "udp"

                addr, port = fields[4].rsplit(":", 1)
                if addr == "*":
                    addr = "0.0.0.0"
                else:
                    ip_version = IpUtil.get_ip_version(addr)
                    if ip_version is None:  # Not a valid ip
                        continue
                    elif ip_version == 6:
                        proto = proto + "6"

                self.log.debug("Got %s %s port %s", addr, proto, port)
                port = int(port)
            except ValueError:
                self.log.exception(
                    "Failed to parse IPService information '%s'", line
                )
                continue

            services.append((proto, port, addr))

        return services


class NetstatServicesParser(BaseParser):
    """Parser class for `/usr/bin/netstat -an | grep ":\\*";` command output.

    Supported format:

        tcp        0      0 0.0.0.0:111         0.0.0.0:*        LISTEN
        tcp        0      0 0.0.0.0:22          0.0.0.0:*        LISTEN
        tcp        0      0 127.0.0.1:25        0.0.0.0:*        LISTEN
        tcp6       0      0 :::111              :::*             LISTEN
        tcp6       0      0 :::22               :::*             LISTEN
        tcp6       0      0 ::1:25              :::*             LISTEN
        udp        0      0 0.0.0.0:68          0.0.0.0:*
        udp        0      0 127.0.0.1:323       0.0.0.0:*
        udp        0      0 0.0.0.0:21944       0.0.0.0:*
        udp6       0      0 :::111              :::*
        udp6       0      0 :::123              :::*
        udp6       0      0 :::37339            :::*
    """

    def parse(self, results):
        """Parses command output in `results` string and returns services
        information in format:

            [(proto, port, addr), ...]
        """
        services = []

        for line in results.split("\n"):
            fields = line.split()
            if len(fields) < 5:
                continue
            try:
                proto = fields[0]
                if proto == "raw":
                    continue
                addr, port = fields[3].rsplit(":", 1)

                self.log.debug("Got %s %s port %s", addr, proto, port)

                port = int(port)
            except ValueError:
                self.log.exception(
                    "Failed to parse IPService information '%s'", line
                )
                continue

            services.append((proto, port, addr))

        return services


class netstat_an(LinuxCommandPlugin):
    """Collect running IP services using `netstat -an` or `ss -lntu`."""

    maptype = "IpServiceMap"
    command = 'export PATH=$PATH:/sbin:/usr/sbin; \
                 if which netstat >/dev/null 2>&1; then \
                     netstat -an | grep ":\\*"; \
                 elif which ss >/dev/null 2>&1; then \
                     echo "### ss output"; ss -lntu; \
                 else \
                     echo "No netstat or ss utilities were found."; exit 127; \
                 fi'

    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = LinuxCommandPlugin.deviceProperties + (
        "zIpServiceMapMaxPort",
    )

    def process(self, device, results, log):
        log.info(
            "Modeler %s processing ip services data for device %s",
            self.name(),
            device.id,
        )
        self.log = log
        rm = self.relMap()
        if not results.strip():  # No output
            log.error("No output from the command: %s", self.command)
            return

        if "### ss output" not in results:
            parser = NetstatServicesParser(log)
        else:
            parser = SsServicesParser(log)

        try:
            maxport = getattr(device, "zIpServiceMapMaxPort", 1024)
            maxport = int(maxport)
        except ValueError:
            maxport = 1024

        rm = self.relMap()
        ports = {}
        for proto, port, addr in parser.parse(results):
            if (
                not IpUtil.isRemotelyReachable(addr) or not port
            ):  # Can't monitor things we can't reach
                continue

            if port > maxport:
                log.debug(
                    "Ignoring entry greater than zIpServiceMapMaxPort "
                    "(%s): %s %s %s",
                    maxport,
                    addr,
                    proto,
                    port,
                )
                continue

            om = ports.get((proto, port), None)
            if om:
                if addr in om.ipaddresses:
                    continue
                log.debug(
                    "Adding %s to the list of addresses listening "
                    "to %s port %s",
                    addr,
                    proto,
                    port,
                )
                om.ipaddresses.append(addr)
            else:
                om = self.objectMap()
                om.protocol = proto
                om.port = int(port)
                om.id = "%s_%05d" % (om.protocol, om.port)
                log.debug(
                    "Found %s listening to %s port %s (%s)",
                    addr,
                    proto,
                    port,
                    om.id,
                )
                om.setServiceClass = {"protocol": proto, "port": om.port}
                om.ipaddresses = [addr]
                om.discoveryAgent = self.name()
                ports[(proto, port)] = om
                rm.append(om)

        log.debug("Found %d IPServices", len(ports.keys()))

        return rm
