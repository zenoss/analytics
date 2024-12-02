##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.EnterpriseOIDs import EnterpriseOIDs
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetMap
from Products.DataCollector.plugins.DataMaps import MultiArgs


class NewDeviceMap(SnmpPlugin):
    """
    Record basic hardware/software information based on the snmpDscr OID.

    Try to determine OS and hardware manufacturer information based on
    the SNMP description (sysDescr).
    """

    maptype = "NewDeviceMap"

    snmpGetMap = GetMap(
        {
            ".1.3.6.1.2.1.1.1.0": "snmpDescr",
            ".1.3.6.1.2.1.1.2.0": "snmpOid",
        }
    )

    osregex = (
        # Novell NetWare 5.00.09 September 21, 2000 Proliant ML370
        re.compile(r"Novell (NetWare \S+)"),
        # Cisco Internetwork Operating System Software IOS (tm) s72033_rp
        # Software (s72033_rp-IPSERVICESK9-M), Version 12.2(18)SXE3, RELEASE
        # SOFTWARE (fc1)
        re.compile(r"(IOS).*Version (\S+),"),
        # Cisco Catalyst Operating System Software, Version 7.6(10)
        re.compile(r"(Cisco Catalyst).*Version (\S+)"),
        # Cisco Systems, Inc./VPN 3000 Concentrator Version 4.1.7.D built
        re.compile(r"(Cisco).*\/(VPN \d+).*Version (\S+)"),
        # Hardware: x86 Family 15 Model 4 Stepping 1 AT/AT COMPATIBLE -
        # Software: Windows Version 5.2 (Build 3790 Multiprocessor Free)
        re.compile(r"- Software: (.+) \(Build"),
        # IBM PowerPC CHRP Computer Machine Type: 0x0800004c Processor id:
        # 000919754C00 Base Operating System Runtime AIX version:
        # 05.02.0000.0050 TCP/IP Client Support version: 05.02.0000.0051
        re.compile(r"^(IBM).*(AIX.*) TCP"),
        # Lantronix SLC
        re.compile(r"(SLC\d+), (Firmware Version .+)"),
        # SunOS testHost 5.10 Generic_138889-05 i86pc
        re.compile(r"^(SunOS) \S+ (\S+) (\S+) (\S+)"),  # Solaris 10
        # GENERIC unix
        re.compile(r"(\S+) \S+ (\S+)"),  # unix
    )

    def process(self, device, results, log):
        """
        Collect SNMP information from this device
        """
        log.info("Processing %s for device %s", self.name(), device.id)
        getdata, tabledata = results
        if not getdata:
            log.warn("Unable to retrieve getdata from %s", device.id)
            log.warn(
                "Does snmpwalk -v1 -c community %s 1.3.6.1.2.1.1 work?",
                device.id,
            )
            return
        log.debug("%s getdata = %s", device.id, getdata)
        om = self.objectMap(getdata)

        # Set the manufacturer according the IANA enterprise OID assignments.
        if om.snmpOid:
            match = re.match(r"(.\d+){7}", om.snmpOid)
            if match:
                manufacturer = EnterpriseOIDs.get(match.group(0), None)
            else:
                manufacturer = None

            om.setHWProductKey = MultiArgs(om.snmpOid, manufacturer)
            log.debug("HWProductKey=%s", om.setHWProductKey)

        if om.snmpDescr:
            descr = re.sub(r"\s", " ", om.snmpDescr)
            for regex in self.osregex:
                m = regex.search(descr)
                if m:
                    groups = m.groups()
                    if groups[0] == "SunOS":
                        om.setOSProductKey = MultiArgs(
                            " ".join(groups[0:3]), "Sun"
                        )
                    else:
                        om.setOSProductKey = " ".join(groups)
                    log.debug("OSProductKey=%s", om.setOSProductKey)
                    break
        return om
