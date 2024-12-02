##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from twisted.internet.utils import getProcessOutput

from Products.DataCollector.plugins.CollectorPlugin import PythonPlugin
from Products.ZenUtils.ZenTales import talesCompile, getEngine

NMAPDEFAULTS = "-p 1-1024 -sT -oG -"


class IpServiceMap(PythonPlugin):
    """
    Uses nmap to model the list of listening TCP ports from any device.
    It should be used when zenoss.snmp.IpServiceMap won't work due to
    IPv6 listeners or if a device has no SNMP support.
    """

    transport = "python"
    maptype = "IpServiceMap"
    compname = "os"
    relname = "ipservices"
    modname = "Products.ZenModel.IpService"
    deviceProperties = PythonPlugin.deviceProperties + (
        "zNmapPortscanOptions",
    )

    def collect(self, device, log):
        nmapoptions = getattr(device, "zNmapPortscanOptions", NMAPDEFAULTS)
        # compile Tales expressions
        tales = readyopts = None
        try:
            tales = talesCompile("string:" + nmapoptions)
            readyopts = tales(
                getEngine().getContext(
                    {"here": device, "device": device, "dev": device}
                )
            )
            readyopts = readyopts + " " + device.manageIp
        # if there was an error make a best effort
        except Exception as e:
            log.error(
                "zNmapPortscanOptions contain illegal Tales expression, "
                "please review: %s",
                e,
            )
            readyopts = NMAPDEFAULTS + " " + device.manageIp
        nmapoptions = readyopts.split(" ")
        log.info(
            "running the following nmap command: %s %s",
            "/usr/bin/nmap",
            " ".join(nmapoptions),
        )
        return getProcessOutput("/usr/bin/nmap", nmapoptions)

    def process(self, device, results, log):
        rm = self.relMap()
        lines = portMatch = None
        # determine grep-friendly vs. std. output
        if results.find("# Nmap") > -1:
            lines = results.split("\n")
            if lines[1]:
                if "Status:" in lines[1]:
                    lines = lines[2].split(" ")
                else:
                    lines = lines[1].split(" ")
            portMatch = re.compile(r"^(\d+)\/open\/tcp")
        else:
            portMatch = re.compile(r"^(\d+)\/tcp\s+open\s+")
            lines = results.split("\n")

        for section in lines:
            match = portMatch.search(section)
            if not match:
                continue
            port = int(match.groups()[0])
            om = self.objectMap()
            om.id = "tcp_%05d" % port
            om.ipaddresses = [
                "0.0.0.0",
            ]
            om.protocol = "tcp"
            om.port = port
            om.setServiceClass = {"protocol": "tcp", "port": port}
            om.discoveryAgent = self.name()
            rm.append(om)

        if len(rm.maps) == 0:
            log.warn(
                "No services found, or nmap output wasn't processed properly."
            )
        return rm
