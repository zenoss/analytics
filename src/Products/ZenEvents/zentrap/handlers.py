##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import ctypes
import logging
import time

from pynetsnmp import netsnmp
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_WARNING

from Products.ZenEvents.EventServer import Stats

from .decode import decode_snmp_value
from .net import SNMPv1, SNMPv2, SNMPv3
from .processors import (
    LegacyVarbindProcessor,
    DirectVarbindProcessor,
    MixedVarbindProcessor,
)

log = logging.getLogger("zen.zentrap.handlers")


class TrapHandler(object):
    """
    Handle raw SNMP traps.
    """

    _varbind_processors = {
        LegacyVarbindProcessor.MODE: LegacyVarbindProcessor,
        DirectVarbindProcessor.MODE: DirectVarbindProcessor,
        MixedVarbindProcessor.MODE: MixedVarbindProcessor,
    }

    def __init__(self, oidmap, copymode, monitor, eventsvc):
        self._oidmap = oidmap
        self._monitor = monitor
        self._eventservice = eventsvc
        self.stats = Stats()

        if copymode not in self._varbind_processors:
            copymode = MixedVarbindProcessor.MODE
            log.warn(
                "Invalid 'varbindCopyMode' value. "
                "'varbindCopyMode=%s' will be used",
                copymode,
            )
        processor_class = self._varbind_processors.get(copymode)
        self._process_varbinds = processor_class(self._oidmap.to_name)

    def __call__(self, addr, pdu, starttime):
        """
        Process a trap.

        @param addr: packet-sending host's IP address, port info
        @type addr: (host-ip, port)
        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        @param starttime: time stamp
        @type starttime: float
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        # Some misbehaving agents will send SNMPv1 traps contained within
        # an SNMPv2c PDU. So we can't trust tpdu.version to determine what
        # version trap exists within the PDU. We need to assume that a
        # PDU contains an SNMPv1 trap if the enterprise_length is greater
        # than zero in addition to the PDU version being 0.
        if pdu.version == SNMPv1 or pdu.enterprise_length > 0:
            log.debug(
                "SNMPv1 trap, Addr: %s PDU Agent Addr: %s",
                addr,
                pdu.agent_addr,
            )
            eventType, result = self.decodeSnmpv1(addr, pdu)
        elif pdu.version in (SNMPv2, SNMPv3):
            log.debug("SNMPv2 or v3 trap, Addr: %s", str(addr))
            eventType, result = self.decodeSnmpV2OrV3(addr, pdu)
        else:
            raise RuntimeError(
                "Bad SNMP version string: '%s'" % (pdu.version,)
            )

        result["zenoss.trap_source_ip"] = addr[0]
        community = self.getCommunity(pdu)
        self.sendTrapEvent(result, community, eventType, starttime)
        log.debug(
            "handled trap  event-type=%s oid=%s snmp-version=%s",
            eventType,
            result["oid"],
            result["snmpVersion"],
        )

    def sendTrapEvent(self, result, community, eventType, starttime):
        summary = "snmp trap %s" % eventType
        log.debug(summary)
        result.setdefault("component", "")
        result.setdefault("eventClassKey", eventType)
        result.setdefault("eventGroup", "trap")
        result.setdefault("severity", SEVERITY_WARNING)
        result.setdefault("summary", summary)
        result.setdefault("community", community)
        result.setdefault("firstTime", starttime)
        result.setdefault("lastTime", starttime)
        result.setdefault("monitor", self._monitor)
        self._eventservice.sendEvent(result)
        self.stats.add(time.time() - starttime)

    def decodeSnmpv1(self, addr, pdu):
        result = {"snmpVersion": "1"}
        result["device"] = addr[0]

        variables = self.getResult(pdu)

        log.debug("SNMPv1 pdu has agent_addr: %s", hasattr(pdu, "agent_addr"))

        if hasattr(pdu, "agent_addr"):
            origin = ".".join(str(i) for i in pdu.agent_addr)
            result["device"] = origin

        enterprise = self.getEnterpriseString(pdu)
        generic = pdu.trap_type
        specific = pdu.specific_type

        result["snmpV1Enterprise"] = enterprise
        result["snmpV1GenericTrapType"] = generic
        result["snmpV1SpecificTrap"] = specific

        # Try an exact match with a .0. inserted between enterprise and
        # specific OID. It seems that MIBs frequently expect this .0.
        # to exist, but the device's don't send it in the trap.
        result["oid"] = "%s.0.%d" % (enterprise, specific)
        name = self._oidmap.to_name(
            result["oid"], exactMatch=True, strip=False
        )

        # If we didn't get a match with the .0. inserted we will try
        # resolving with the .0. inserted and allow partial matches.
        if name == result["oid"]:
            result["oid"] = "%s.%d" % (enterprise, specific)
            name = self._oidmap.to_name(
                result["oid"], exactMatch=False, strip=False
            )

        # Look for the standard trap types and decode them without
        # relying on any MIBs being loaded.
        eventType = {
            0: "coldStart",
            1: "warmStart",
            2: "snmp_linkDown",
            3: "snmp_linkUp",
            4: "authenticationFailure",
            5: "egpNeighorLoss",
            6: name,
        }.get(generic, name)

        # Decode all variable bindings. Allow partial matches and strip
        # off any index values.
        varbinds = []
        for vb_oid, vb_value in variables:
            vb_value = decode_snmp_value(vb_value)
            vb_oid = ".".join(map(str, vb_oid))
            if vb_value is None:
                log.debug(
                    "[decodeSnmpv1] enterprise %s, varbind-oid %s, "
                    "varbind-value %s",
                    enterprise,
                    vb_oid,
                    vb_value,
                )
            varbinds.append((vb_oid, vb_value))

        result.update(self._process_varbinds(varbinds))

        return eventType, result

    def decodeSnmpV2OrV3(self, addr, pdu):
        eventType = "unknown"
        version = "2" if pdu.version == SNMPv2 else "3"
        result = {"snmpVersion": version, "oid": "", "device": addr[0]}
        variables = self.getResult(pdu)

        varbinds = []
        for vb_oid, vb_value in variables:
            vb_value = decode_snmp_value(vb_value)
            vb_oid = ".".join(map(str, vb_oid))
            if vb_value is None:
                log.debug(
                    "[decodeSnmpV2OrV3] varbind-oid %s, varbind-value %s",
                    vb_oid,
                    vb_value,
                )

            # SNMPv2-MIB/snmpTrapOID
            if vb_oid == "1.3.6.1.6.3.1.1.4.1.0":
                result["oid"] = vb_value
                eventType = self._oidmap.to_name(
                    vb_value, exactMatch=False, strip=False
                )
            elif vb_oid.startswith("1.3.6.1.6.3.18.1.3"):
                log.debug(
                    "found snmpTrapAddress OID: %s = %s", vb_oid, vb_value
                )
                result["snmpTrapAddress"] = vb_value
                result["device"] = vb_value
            else:
                varbinds.append((vb_oid, vb_value))

        result.update(self._process_varbinds(varbinds))

        if eventType in ["linkUp", "linkDown"]:
            eventType = "snmp_" + eventType

        return eventType, result

    def getEnterpriseString(self, pdu):
        """
        Get the enterprise string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: enterprise string
        @rtype: string
        """
        return ".".join(
            str(pdu.enterprise[i]) for i in range(pdu.enterprise_length)
        )

    def getResult(self, pdu):
        """
        Get the values from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: variables from the PDU or Fake packet
        @rtype: dictionary
        """
        return netsnmp.getResult(pdu, log)

    def getCommunity(self, pdu):
        """
        Get the community string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: SNMP community
        @rtype: string
        """
        if pdu.community_len:
            return ctypes.string_at(pdu.community, pdu.community_len)
        return ""


class ReplayTrapHandler(TrapHandler):
    """
    Handle replayed SNMP traps.

    Used for replaying capture SNMP trap packets.
    """

    def getEnterpriseString(self, pdu):
        """
        Get the enterprise string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: FakePacket
        @return: enterprise string
        @rtype: string
        """
        return pdu.enterprise

    def getResult(self, pdu):
        """
        Get the values from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: FakePacket
        @return: variables from the PDU or Fake packet
        @rtype: dictionary
        """
        return pdu.variables

    def getCommunity(self, pdu):
        """
        Get the community string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: FakePacket
        @return: SNMP community
        @rtype: string
        """
        return pdu.community
