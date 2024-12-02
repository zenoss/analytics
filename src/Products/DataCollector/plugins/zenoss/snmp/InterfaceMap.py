##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re

from Products.DataCollector.plugins.CollectorPlugin import (
    GetTableMap,
    SnmpPlugin,
)
from Products.ZenUtils import IpUtil
from Products.ZenUtils.Utils import cleanstring, unsigned


class InterfaceMap(SnmpPlugin):
    """
    Map IPv4 and IPv6 network names and aliases to DMD 'interface' objects
    """

    order = 80
    compname = "os"
    relname = "interfaces"
    modname = "Products.ZenModel.IpInterface"
    deviceProperties = SnmpPlugin.deviceProperties + (
        "zInterfaceMapIgnoreNames",
        "zInterfaceMapIgnoreTypes",
        "zInterfaceMapIgnoreDescriptions",
    )

    # Interface related tables likely to be used in all subclasses.
    baseSnmpGetTableMaps = (
        GetTableMap(
            "iftable",
            ".1.3.6.1.2.1.2.2.1",
            {
                ".1": "ifindex",
                ".2": "id",
                ".3": "type",
                ".4": "mtu",
                ".5": "speed",
                ".6": "macaddress",
                ".7": "adminStatus",
                ".8": "operStatus",
            },
        ),
        # ipAddrTable is the better way to get IP addresses
        GetTableMap(
            "ipAddrTable",
            ".1.3.6.1.2.1.4.20.1",
            {".1": "ipAddress", ".2": "ifindex", ".3": "netmask"},
        ),
        # IP-MIB::ipAddressIfIndex can give us IPv6 addresses.
        GetTableMap(
            "ipAddressIfIndex",
            ".1.3.6.1.2.1.4.34.1.3.2",
            {
                ".16": "ifindex",
            },
        ),
        GetTableMap(
            "ipAddressPrefix", ".1.3.6.1.2.1.4.34.1.5.2", {".16": "netmaskv6"}
        ),
        # Use the ipNetToMediaTable as a backup to the ipAddrTable
        GetTableMap(
            "ipNetToMediaTable",
            ".1.3.6.1.2.1.4.22.1",
            {".1": "ifindex", ".3": "ipaddress", ".4": "iptype"},
        ),
        # attempt to determine if the interface supports duplex mode
        GetTableMap("duplex", ".1.3.6.1.2.1.10.7.2.1", {".19": "duplex"}),
    )

    # Base interface tables, plus ones used locally.
    snmpGetTableMaps = baseSnmpGetTableMaps + (
        # Extended interface information.
        GetTableMap(
            "ifalias",
            ".1.3.6.1.2.1.31.1.1.1",
            {
                ".6": "ifHCInOctets",
                ".7": "ifHCInUcastPkts",
                ".15": "highSpeed",
                ".18": "description",
            },
        ),
    )

    def process(self, device, results, log):
        """
        From SNMP info gathered from the device, convert them
        to interface objects.
        """
        getdata, tabledata = results
        log.info(
            "Modeler %s processing data for device %s", self.name(), device.id
        )
        log.debug("%s tabledata = %s", device.id, tabledata)
        rm = self.relMap()
        iptable = tabledata.get("ipAddrTable")
        sourceTable = "ipAddrTable"
        if not iptable:
            iptable = tabledata.get("ipNetToMediaTable")
            if iptable:
                log.info(
                    "Unable to use ipAddrTable -- "
                    "using ipNetToMediaTable instead"
                )
                sourceTable = "ipNetToMediaTable"
            else:
                log.warn(
                    "Unable to get data for %s from either ipAddrTable or"
                    " ipNetToMediaTable",
                    device.id,
                )
                iptable = dict()

        # Add in IPv6 info
        ipv6table = tabledata.get("ipAddressIfIndex")
        ipv6netmasktable = tabledata.get("ipAddressPrefix")
        if ipv6table and ipv6netmasktable:
            for key in ipv6table.keys():
                ipv6table[key].update(ipv6netmasktable[key])
            iptable.update(ipv6table)

        iftable = tabledata.get("iftable")
        if iftable is None:
            log.error(
                "Unable to get data for %s for iftable -- skipping model",
                device.id,
            )
            return None

        ifalias = tabledata.get("ifalias", {})

        self.prepIfTable(log, iftable, ifalias)

        omtable = {}
        duplex = tabledata.get("duplex", {})
        for key, iface in iftable.items():
            if key in duplex:
                iftable[key]["duplex"] = duplex[key].get("duplex", 0)
            else:
                iftable[key]["duplex"] = 0

        for ip, row in iptable.items():
            # FIXME - not getting ifindex back from HP printer
            if "ifindex" not in row:
                log.debug("IP entry for %s is missing ifindex", ip)
                continue

            ip_parts = ip.split(".")
            # If the ipAddrTable key has five octets, that probably
            # means this is a classless subnet (that is, <256).  Usually,
            # the first 4 octets will be the ipAddress we care about.
            # Regardless, we will be using the ip address in the row
            # later anyway.

            try:
                if len(ip_parts) == 5 and sourceTable == "ipAddrTable":
                    addr_type = IpUtil.IPV4_ADDR_TYPE
                    ip = IpUtil.bytesToCanonIp(ip_parts[:-1])

                # If we are using the ipNetToMediaTable, we use the
                # last 4 octets.
                elif len(ip_parts) == 5 and sourceTable == "ipNetToMediaTable":
                    addr_type = IpUtil.IPV4_ADDR_TYPE
                    if row["iptype"] != 1:
                        log.debug(
                            "iptype (%s) is not 1 -- skipping", row["iptype"]
                        )
                        continue
                    ip = IpUtil.bytesToCanonIp(ip_parts[1:])
                    log.warn("Can't find netmask -- using /24")
                    row["netmask"] = "255.255.255.0"

                elif len(ip_parts) == 16:
                    addr_type = IpUtil.IPV6_ADDR_TYPE
                    ip = IpUtil.bytesToCanonIp(ip_parts)

            except Exception:
                log.warn(
                    "The %s address for ifindex %s is incorrect: %s",
                    addr_type,
                    row["ifindex"],
                    ip,
                )
                continue

            strindex = str(row["ifindex"])
            if strindex not in omtable and strindex not in iftable:
                log.warn(
                    "Skipping %s as it points to missing ifindex %s",
                    row.get("ipAddress", ""),
                    row.get("ifindex", ""),
                )
                continue

            if strindex not in omtable:
                om = self.processInt(log, device, iftable[strindex])
                if not om:
                    continue
                rm.append(om)
                omtable[strindex] = om
                del iftable[strindex]
            elif strindex in omtable:
                om = omtable[strindex]
            else:
                log.warn(
                    "The IP %s points to missing ifindex %s -- skipping",
                    ip,
                    strindex,
                )
                continue

            if not hasattr(om, "setIpAddresses"):
                om.setIpAddresses = []
            if "ipAddress" in row:
                ip = row["ipAddress"]
            if "netmask" in row:
                ip = ip + "/" + str(self.maskToBits(row["netmask"].strip()))
            if "netmaskv6" in row:
                ip = ip + "/" + row["netmaskv6"].split(".")[-1]

            # Ignore IP addresses with a 0.0.0.0 netmask.
            if ip.endswith("/0"):
                log.warn("Ignoring IP address with 0.0.0.0 netmask: %s", ip)
            else:
                om.setIpAddresses.append(ip)

        for iface in iftable.values():
            om = self.processInt(log, device, iface)
            if om:
                rm.append(om)

        return rm

    def prepIfTable(self, log, iftable, ifalias):
        """
        Add interface alias (Cisco description) to iftable
        Sanity check speed
        """
        for ifidx, data in ifalias.items():
            log.debug("ifalias %s raw data = %s", ifidx, data)
            if ifidx not in iftable:
                log.debug("ifidx %s is not in iftable -- skipping", ifidx)
                continue

            # Use row's index if no ifIndex column exists for the row.
            iftable[ifidx].setdefault("ifindex", ifidx.strip("."))

            iftable[ifidx]["description"] = data.get("description", "")

            # handle 10GB interfaces using IF-MIB::ifHighSpeed
            speed = iftable[ifidx].get("speed", 0)
            if speed == 4294967295 or speed == 1410065408 or speed < 0:
                try:
                    iftable[ifidx]["speed"] = data["highSpeed"] * 1e6
                except KeyError:
                    pass

            # Detect availability of the high-capacity counters
            if (
                data.get("ifHCInOctets", None) is not None
                and data.get("ifHCInUcastPkts", None) is not None
            ):
                iftable[ifidx]["hcCounters"] = True

        for ifidx, data in iftable.items():
            try:
                data["speed"] = unsigned(data["speed"])
            except KeyError:
                pass

    def processInt(self, log, device, iface):
        """
        Convert each interface into an object map, if possible
        Return None if the zProperties match the name or type
        of this iface.
        """
        om = self.objectMap(iface)
        if not hasattr(om, "id"):
            log.debug(
                "Can't find 'id' after self.objectMap(iface)"
                " -- ignoring this interface"
            )
            return None

        om.id = cleanstring(om.id)  # take off \x00 at end of string
        # Left in interfaceName, but added title for
        # the sake of consistency
        if not om.id:
            om.id = "Index_%s" % iface.get("ifindex", "")
        om.interfaceName = om.id
        om.title = om.id
        om.id = self.prepId(om.interfaceName)
        if not om.id:
            log.debug(
                "prepId(%s) doesn't return an id -- skipping", om.interfaceName
            )
            return None

        dontCollectIntNames = getattr(device, "zInterfaceMapIgnoreNames", None)
        if dontCollectIntNames and re.search(
            dontCollectIntNames, om.interfaceName
        ):
            log.debug(
                "Interface %s matched the zInterfaceMapIgnoreNames zprop '%s'",
                om.interfaceName,
                getattr(device, "zInterfaceMapIgnoreNames"),
            )
            return None

        om.type = self.ifTypes.get(str(getattr(om, "type", 1)), "Unknown")
        dontCollectIntTypes = getattr(device, "zInterfaceMapIgnoreTypes", None)
        if dontCollectIntTypes and re.search(dontCollectIntTypes, om.type):
            log.debug(
                "Interface %s type %s matched the zInterfaceMapIgnoreTypes "
                "zprop '%s'",
                om.interfaceName,
                om.type,
                getattr(device, "zInterfaceMapIgnoreTypes"),
            )
            return None

        if hasattr(om, "description"):
            dontCollectIntDescriptions = getattr(
                device, "zInterfaceMapIgnoreDescriptions", None
            )
            if dontCollectIntDescriptions and re.search(
                dontCollectIntDescriptions, om.description
            ):
                log.debug(
                    "Interface %s description %s matched the "
                    "zInterfaceMapIgnoreDescriptions zprop '%s'",
                    om.interfaceName,
                    om.description,
                    getattr(device, "zInterfaceMapIgnoreDescriptions"),
                )
                return None

        # Append _64 to interface type if high-capacity counters are supported
        if hasattr(om, "hcCounters"):
            om.type += "_64"
            del om.hcCounters

        if hasattr(om, "macaddress"):
            if isinstance(om.macaddress, basestring):
                om.macaddress = self.asmac(om.macaddress)
            else:
                log.debug(
                    "The MAC address for interface %s is invalid (%s)"
                    " -- ignoring",
                    om.id,
                    om.macaddress,
                )

        # Handle misreported operStatus from Linux tun devices
        if om.id.startswith("tun") and om.adminStatus == 1:
            om.operStatus = 1

        # Net-SNMP on Linux will always report the speed of bond interfaces as
        # 10Mbps. This is probably due to the complexity of figuring out the
        # real speed which would take into account all bonded interfaces and
        # the bonding method (aggregate/failover). The problem is that 10Mbps
        # is a really bad default. The following check changes this default to
        # 1Gbps instead. See the following article that explains how you can
        # manually set this per-interface in the device's snmpd.conf for better
        # accuracy.
        #
        # http://whocares.de/2007/12/28/speed-up-your-bonds/
        if om.id.startswith("bond") and om.speed == 1e7:
            newspeed = 1000000000
            log.debug(
                "Resetting bond interface %s speed from %s to %s",
                om.interfaceName,
                om.speed,
                newspeed,
            )
            om.speed = newspeed

        # Clear out all IP addresses for interfaces that no longer have any.
        if not hasattr(om, "setIpAddresses"):
            om.setIpAddresses = []

        return om

    ifTypes = {
        "1": "Other",
        "2": "regular1822",
        "3": "hdh1822",
        "4": "ddnX25",
        "5": "rfc877x25",
        "6": "ethernetCsmacd",
        "7": "iso88023Csmacd",
        "8": "iso88024TokenBus",
        "9": "iso88025TokenRing",
        "10": "iso88026Man",
        "11": "starLan",
        "12": "proteon10Mbit",
        "13": "proteon80Mbit",
        "14": "hyperchannel",
        "15": "fddi",
        "16": "lapb",
        "17": "sdlc",
        "18": "ds1",
        "19": "e1",
        "20": "basicISDN",
        "21": "primaryISDN",
        "22": "propPointToPointSerial",
        "23": "ppp",
        "24": "softwareLoopback",
        "25": "eon",
        "26": "ethernet-3Mbit",
        "27": "nsip",
        "28": "slip",
        "29": "ultra",
        "30": "ds3",
        "31": "sip",
        "32": "frame-relay",
        "33": "rs232",
        "34": "para",
        "35": "arcnet",
        "36": "arcnetPlus",
        "37": "atm",
        "38": "miox25",
        "39": "sonet",
        "40": "x25ple",
        "41": "iso88022llc",
        "42": "localTalk",
        "43": "smdsDxi",
        "44": "frameRelayService",
        "45": "v35",
        "46": "hssi",
        "47": "hippi",
        "48": "modem",
        "49": "aal5",
        "50": "sonetPath",
        "51": "sonetVT",
        "52": "smdsIcip",
        "53": "propVirtual",
        "54": "propMultiplexor",
        "55": "100BaseVG",
        "56": "Fibre Channel",
        "57": "HIPPI Interface",
        "58": "Obsolete for FrameRelay",
        "59": "ATM Emulation of 802.3 LAN",
        "60": "ATM Emulation of 802.5 LAN",
        "61": "ATM Emulation of a Circuit",
        "62": "FastEthernet (100BaseT)",
        "63": "ISDN",
        "64": "CCITT V.11_X.21",
        "65": "CCITT V.36",
        "66": "CCITT G703 at 64Kbps",
        "67": "Obsolete G702 see DS1-MIB",
        "68": "SNA QLLC",
        "69": "Full Duplex Fast Ethernet (100BaseFX)",
        "70": "Channel",
        "71": "Radio Spread Spectrum (802.11)",
        "72": "IBM System 360_370 OEMI Channel",
        "73": "IBM Enterprise Systems Connection",
        "74": "Data Link Switching",
        "75": "ISDN S_T Interface",
        "76": "ISDN U Interface",
        "77": "Link Access Protocol D (LAPD)",
        "78": "IP Switching Opjects",
        "79": "Remote Source Route Bridging",
        "80": "ATM Logical Port",
        "81": "ATT DS0 Point (64 Kbps)",
        "82": "ATT Group of DS0 on a single DS1",
        "83": "BiSync Protocol (BSC)",
        "84": "Asynchronous Protocol",
        "85": "Combat Net Radio",
        "86": "ISO 802.5r DTR",
        "87": "Ext Pos Loc Report Sys",
        "88": "Apple Talk Remote Access Protocol",
        "89": "Proprietary Connectionless Protocol",
        "90": "CCITT-ITU X.29 PAD Protocol",
        "91": "CCITT-ITU X.3 PAD Facility",
        "92": "MultiProtocol Connection over Frame_Relay",
        "93": "CCITT-ITU X213",
        "94": "Asymetric Digitial Subscriber Loop (ADSL)",
        "95": "Rate-Adapt Digital Subscriber Loop (RDSL)",
        "96": "Symetric Digitial Subscriber Loop (SDSL)",
        "97": "Very High Speed Digitial Subscriber Loop (HDSL)",
        "98": "ISO 802.5 CRFP",
        "99": "Myricom Myrinet",
        "100": "Voice recEive and transMit (voiceEM)",
        "101": "Voice Foreign eXchange Office (voiceFXO)",
        "102": "Voice Foreign eXchange Station (voiceFXS)",
        "103": "Voice Encapulation",
        "104": "Voice Over IP Encapulation",
        "105": "ATM DXI",
        "106": "ATM FUNI",
        "107": "ATM IMA",
        "108": "PPP Multilink Bundle",
        "109": "IBM IP over CDLC",
        "110": "IBM Common Link Access to Workstation",
        "111": "IBM Stack to Stack",
        "112": "IBM Virtual IP Address (VIPA)",
        "113": "IBM Multi-Protocol Channel Support",
        "114": "IBM IP over ATM",
        "115": "ISO 802.5j Fiber Token Ring",
        "116": "IBM Twinaxial Data Link Control (TDLC)",
        "117": "Gigabit Ethernet",
        "118": "Higher Data Link Control (HDLC)",
        "119": "Link Access Protocol F (LAPF)",
        "120": "CCITT V.37",
        "121": "CCITT X.25 Multi-Link Protocol",
        "122": "CCITT X.25 Hunt Group",
        "123": "Transp HDLC",
        "124": "Interleave Channel",
        "125": "Fast Channel",
        "126": "IP (for APPN HPR in IP Networks)",
        "127": "CATV MAC Layer",
        "128": "CATV Downstream Interface",
        "129": "CATV Upstream Interface",
        "130": "Avalon Parallel Processor",
        "131": "Encapsulation Interface",
        "132": "Coffee Pot",
        "133": "Circuit Emulation Service",
        "134": "ATM Sub Interface",
        "135": "Layer 2 Virtual LAN using 802.1Q",
        "136": "Layer 3 Virtual LAN using IP",
        "137": "Layer 3 Virtual LAN using IPX",
        "138": "IP Over Power Lines",
        "139": "Multi-Media Mail over IP",
        "140": "Dynamic synchronous Transfer Mode (DTM)",
        "141": "Data Communications Network",
        "142": "IP Forwarding Interface",
        "143": "Multi-rate Symmetric DSL",
        "144": "IEEE1394 High Performance Serial Bus",
        "145": "HIPPI-6400",
        "146": "DVB-RCC MAC Layer",
        "147": "DVB-RCC Downstream Channel",
        "148": "DVB-RCC Upstream Channel",
        "149": "ATM Virtual Interface",
        "150": "MPLS Tunnel Virtual Interface",
        "151": "Spatial Reuse Protocol",
        "152": "Voice Over ATM",
        "153": "Voice Over Frame Relay",
        "154": "Digital Subscriber Loop over ISDN",
        "155": "Avici Composite Link Interface",
        "156": "SS7 Signaling Link",
        "157": "Prop. P2P wireless interface",
        "158": "Frame Forward Interface",
        "159": "Multiprotocol over ATM AAL5",
        "160": "USB Interface",
        "161": "IEEE 802.3ad Link Aggregate",
        "162": "BGP Policy Accounting",
        "163": "FRF .16 Multilink Frame Relay",
        "164": "H323 Gatekeeper",
        "165": "H323 Voice and Video Proxy",
        "166": "MPLS",
        "167": "Multi-frequency signaling link",
        "168": "High Bit-Rate DSL - 2nd generation",
        "169": "Multirate HDSL2",
        "170": "Facility Data Link 4Kbps on a DS1",
        "171": "Packet over SONET_SDH Interface",
        "172": "DVB-ASI Input",
        "173": "DVB-ASI Output",
        "174": "Power Line Communtications",
        "175": "Non Facility Associated Signaling",
        "176": "TR008",
        "177": "Remote Digital Terminal",
        "178": "Integrated Digital Terminal",
        "179": "ISUP",
        "180": "prop_Maclayer",
        "181": "prop_Downstream",
        "182": "prop_Upstream",
        "183": "HIPERLAN Type 2 Radio Interface",
        "184": "PropBroadbandWirelessAccesspt2multipt",
        "185": "SONET Overhead Channel",
        "186": "Digital Wrapper",
        "187": "ATM adaptation layer 2",
        "188": "MAC layer over radio links",
        "189": "ATM over radio links",
        "190": "Inter Machine Trunks",
        "191": "Multiple Virtual Lines DSL",
        "192": "Long Rach DSL",
        "193": "Frame Relay DLCI End Point",
        "194": "ATM VCI End Point",
        "195": "Optical Channel",
        "196": "Optical Transport",
        "197": "Proprietary ATM",
        "198": "Voice Over Cable Interface",
        "199": "Infiniband",
        "200": "TE Link",
        "201": "Q.2931",
        "202": "Virtual Trunk Group",
        "203": "SIP Trunk Group",
        "204": "SIP Signaling",
        "205": "CATV Upstream Channel",
        "206": "Acorn Econet",
        "207": "FSAN 155Mb Symetrical PON interface",
        "208": "FSAN622Mb Symetrical PON interface",
        "209": "Transparent bridge interface",
        "210": "Interface common to multiple lines",
        "211": "voice E and M Feature Group D",
        "212": "voice FGD Exchange Access North American",
        "213": "voice Direct Inward Dialing",
        "214": "MPEG transport interface",
        "215": "6to4 interface (DEPRECATED)",
        "216": "GTP (GPRS Tunneling Protocol)",
        "217": "Paradyne EtherLoop 1",
        "218": "Paradyne EtherLoop 2",
        "219": "Optical Channel Group",
        "220": "HomePNA ITU-T G.989",
        "221": "Generic Framing Procedure (GFP)",
        "222": "Layer 2 Virtual LAN using Cisco ISL",
        "223": "Acteleis proprietary MetaLOOP High Speed Link",
        "224": "FCIP Link",
        "225": "Resilient Packet Ring Interface Type",
        "226": "RF Qam Interface",
        "227": "Link Management Protocol",
        "228": "Cambridge Broadband Limited VectaStar",
        "229": "CATV Modular CMTS Downstream Interface",
        "230": "Asymmetric Digital Subscriber Loop Version 2",
        "231": "MACSecControlled",
        "232": "MACSecUncontrolled",
    }
