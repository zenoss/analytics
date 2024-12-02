##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import LinuxCommandPlugin

speedPattern = re.compile(r"(\d+)\s*[gm]bps", re.I)


def parseDmesg(dmesg, relMap):
    """
    parseDmesg to get interface speed.
    """
    for line in dmesg.splitlines():
        speedMatch = speedPattern.search(line)
        if speedMatch:
            for objMap in relMap.maps:
                if objMap.interfaceName in line:
                    if "Gbps" in speedMatch.group(0):
                        objMap.speed = int(speedMatch.group(1)) * 1e9
                    else:
                        objMap.speed = int(speedMatch.group(1)) * 1e6
                    break
    return relMap


class ifconfig(LinuxCommandPlugin):
    """Maps a linux ifconfig command to the interfaces relation."""

    # echo __COMMAND__ is used to delimit the results
    command = 'export PATH=$PATH:/sbin:/usr/sbin; \
               if which ifconfig >/dev/null 2>&1; then \
                   ifconfig -a; \
               elif which ip >/dev/null 2>&1; then \
                   echo "### ip addr output"; ip addr; \
               else \
                   echo "No ifconfig or ip utilities were found."; exit 127; \
               fi  && echo __COMMAND__ && /bin/dmesg'
    compname = "os"
    relname = "interfaces"
    modname = "Products.ZenModel.IpInterface"
    deviceProperties = LinuxCommandPlugin.deviceProperties + (
        "zInterfaceMapIgnoreNames",
        "zInterfaceMapIgnoreTypes",
    )

    # variables for ifconfig
    ifstart = re.compile(r"^(\S+?):?\s+")
    oldiftype = re.compile(
        r"^\S+\s+Link encap:(.+)HWaddr (\S+)|^\S+\s+Link encap:(.+)"
    )
    v4addr = re.compile(
        r"inet addr:(\S+).*Mask:(\S+)|inet\s+(\S+)\s+netmask\s+(\S+)"
    )
    v6addr = re.compile(
        r"inet6 addr: (\S+).*|inet6\s+(\S+)\s+prefixlen\s+(\d+)"
    )
    flags = re.compile(
        r"^(.*) MTU:(\d+)\s+Metric:.*"
        r"|^\S+:\s+flags=\d+<(\S+)>\s+mtu\s+(\d+)"
    )
    newether = re.compile(r"^\s+ether\s+(\S+)")
    newifctype = re.compile(r"txqueuelen\s+\d+\s+\(([^)]+)\)")

    # variables for ip tool (ip addr)
    ip_ifstart = re.compile(r"^(\d+):\s(\S+):\s(.*)mtu\s(\d+)(.*)")
    ip_v4addr = re.compile(r"inet (\S+)")
    ip_v6addr = re.compile(r"inet6 (\S+)")
    ip_hwaddr = re.compile(r"link/(\S+)\s(\S+)")

    def process(self, device, results, log):
        log.info(
            "Modeler %s processing data for device %s", self.name(), device.id
        )
        self.log = log
        ifconfig, dmesg = results.split("__COMMAND__")
        if "###" in ifconfig:
            relMap = self.parseIpconfig(ifconfig, device, self.relMap())
        else:
            relMap = self.parseIfconfig(ifconfig, device, self.relMap())
        relMap = parseDmesg(dmesg.lstrip(), relMap)
        return relMap

    def parseIfconfig(self, ifconfig, device, relMap):
        """
        Parse the output of the ifconfig -a command.
        """
        rlines = ifconfig.splitlines()
        iface = None
        for line in rlines:

            # reset state to no interface
            if not line.strip():
                iface = None

            # new interface starting
            miface = self.ifstart.search(line)
            if miface:
                # start new interface and get name, type, and macaddress
                iface = self.objectMap()
                name = miface.group(1)

                iface.interfaceName = name
                iface.id = self.prepId(name)
                if self.isIgnoredName(device, iface.interfaceName):
                    continue

                relMap.append(iface)

            mtype = self.oldiftype.search(line)
            if mtype:
                if mtype.lastindex == 2:
                    itype, iface.macaddress = mtype.groups()[:2]
                else:
                    itype = mtype.group(3)

                if itype.startswith("Ethernet"):
                    itype = "ethernetCsmacd"
                iface.type = itype.strip()

                if self.isIgnoredType(device, iface.interfaceName, iface.type):
                    relMap.maps.remove(iface)
                    iface = None

                    continue

            # get the IP addresses of an interface
            maddr = self.v4addr.search(line)
            if maddr and iface:
                # get IP address and netmask
                if maddr.lastindex == 2:
                    ip, netmask = maddr.groups()[:2]
                else:
                    ip, netmask = maddr.groups()[2:]
                netmask = self.maskToBits(netmask)
                if not hasattr(iface, "setIpAddresses"):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append("%s/%s" % (ip, netmask))

            maddr = self.v6addr.search(line)
            if maddr and iface:
                # get IP address
                if maddr.lastindex == 3:
                    ip = "%s/%s" % maddr.groups()[1:]
                else:
                    ip = maddr.group(1)
                if not hasattr(iface, "setIpAddresses"):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append(ip)

            mether = self.newether.search(line)
            if mether and iface:
                # get MAC address (new style)
                macaddress = mether.group(1)
                iface.macaddress = macaddress

                iface.type = "ethernetCsmacd"

                if self.isIgnoredType(device, iface.interfaceName, iface.type):
                    relMap.maps.remove(iface)
                    iface = None

                continue

            mtype = self.newifctype.search(line)
            if mtype and iface:
                # get MAC address (new style)
                ifctype = mtype.group(1)

                iface.type = ifctype.strip()

                if self.isIgnoredType(device, iface.interfaceName, iface.type):
                    relMap.maps.remove(iface)
                    iface = None

                    continue

            # get the state UP/DOWN of the interface
            mstatus = self.flags.search(line)
            if mstatus and iface:
                # get adminStatus, operStatus, and mtu
                if mstatus.lastindex == 2:
                    flags, mtu = mstatus.groups()[:2]
                else:
                    flags, mtu = mstatus.groups()[2:]
                if "UP" in flags:
                    iface.operStatus = 1
                else:
                    iface.operStatus = 2
                if "RUNNING" in flags:
                    iface.adminStatus = 1
                else:
                    iface.adminStatus = 2
                iface.mtu = int(mtu)

        return relMap

    def parseIpconfig(self, ifconfig, device, relMap):
        """
        Parse the output of the ip addr command.
        """
        rlines = ifconfig.splitlines()
        iface = None
        for line in rlines:
            # reset state to no interface
            if not line.strip():
                iface = None

            # new interface starting
            miface = self.ip_ifstart.search(line)
            if miface:
                # start new interface and get name, type, and macaddress
                iface = self.objectMap()
                no, name, flags, mtu = miface.groups()[:4]
                iface.interfaceName = name
                iface.id = self.prepId(name)
                dontCollectIntNames = getattr(
                    device, "zInterfaceMapIgnoreNames", None
                )
                if dontCollectIntNames and re.search(
                    dontCollectIntNames, iface.interfaceName
                ):
                    self.log.debug(
                        "Interface %s matched the zInterfaceMapIgnoreNames "
                        "zprop '%s'",
                        iface.interfaceName,
                        dontCollectIntNames,
                    )
                    continue

                dontCollectIntTypes = getattr(
                    device, "zInterfaceMapIgnoreTypes", None
                )
                if dontCollectIntTypes and re.search(
                    dontCollectIntTypes, iface.type
                ):
                    self.log.debug(
                        "Interface %s type %s matched the "
                        "zInterfaceMapIgnoreTypes zprop '%s'",
                        iface.interfaceName,
                        iface.type,
                        dontCollectIntTypes,
                    )
                    continue

                relMap.append(iface)

                if "UP" in flags:
                    iface.operStatus = 1
                else:
                    iface.operStatus = 2
                if "LOWER_UP" in flags:
                    iface.adminStatus = 1
                else:
                    iface.adminStatus = 2

                if mtu:
                    iface.mtu = int(mtu)
                continue

            # get the IP addresses of an interface
            maddr = self.ip_v4addr.search(line)
            if maddr and iface:
                # get IP address and netmask
                _ip = str(maddr.groups()[:1]).translate(None, r"\(\)', ")
                _ip = _ip.split("/")
                ip = _ip[0]
                netmask = _ip[1]
                if not hasattr(iface, "setIpAddresses"):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append("%s/%s" % (ip, netmask))

            maddr = self.ip_v6addr.search(line)
            if maddr and iface:
                # get IP address
                ip = maddr.groups()[0]
                if not hasattr(iface, "setIpAddresses"):
                    iface.setIpAddresses = []
                iface.setIpAddresses.append(ip)

            # get macaddress
            maddr = self.ip_hwaddr.search(line)
            if maddr and iface:
                iface.macaddress = maddr.groups()[1]
                itype = maddr.groups()[0].replace("link/", "", 1)
                if itype.startswith("ether"):
                    itype = "ethernetCsmacd"
                elif itype.startswith("loopback"):
                    itype = "Local Loopback"
                iface.type = itype.strip()
        return relMap

    def isIgnoredName(self, device, name):
        """Checks whether interface name in device's ignore list."""
        dontCollectIntNames = getattr(device, "zInterfaceMapIgnoreNames", None)
        if dontCollectIntNames and re.search(dontCollectIntNames, name):
            self.log.debug(
                "Interface %s matched the "
                "zInterfaceMapIgnoreNames zprop '%s'",
                name,
                dontCollectIntNames,
            )
            return True
        return False

    def isIgnoredType(self, device, name, ifcType):
        """Checks whether interface type in device's ignore list."""
        dontCollectIntTypes = getattr(device, "zInterfaceMapIgnoreTypes", None)
        if dontCollectIntTypes and re.search(dontCollectIntTypes, ifcType):
            self.log.debug(
                "Interface %s type %s matched the "
                "zInterfaceMapIgnoreTypes zprop '%s'",
                name,
                ifcType,
                dontCollectIntTypes,
            )
            return True
        return False
