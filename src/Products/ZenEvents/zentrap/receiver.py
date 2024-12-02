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
import socket
import time

from ipaddr import IPAddress
from pynetsnmp import netsnmp, twistedsnmp

from .net import (
    ipv6_is_enabled,
    pre_parse_factory,
    SNMPv1,
    SNMPv2,
    SNMPv3,
    sockaddr_in,
    sockaddr_in6,
)

log = logging.getLogger("zen.zentrap.receiver")


class Receiver(object):
    """
    Listen for SNMP traps.
    """

    def __init__(self, options, handler):
        self._port = options.trapport
        self._handler = handler

        listening_protocol = "udp6" if ipv6_is_enabled() else "udp"
        if options.useFileDescriptor is not None:
            self._address = listening_protocol + ":1162"
            self._fileno = int(options.useFileDescriptor)
        else:
            self._address = "%s:%d" % (listening_protocol, self._port)
            self._fileno = -1

        self._pre_parse_callback = pre_parse_factory(_pre_parse)

    @property
    def handler(self):
        return self._handler

    def start(self):
        # Start listening for SNMP traps
        self._session = netsnmp.Session()
        self._session.awaitTraps(
            self._address, self._fileno, self._pre_parse_callback, debug=True
        )
        self._session.callback = self._receive_packet
        twistedsnmp.updateReactor()
        log.info("listening for SNMP traps  port=%s", self._port)

    def stop(self):
        if self._session:
            self._session.close()
            self._session = None

    def create_users(self, users):
        if self._session is None:
            log.debug("No session created, so unable to create users")
        else:
            self._session.create_users(users)

    def _receive_packet(self, pdu):
        """
        Accept a packet from the network.

        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        """
        start_time = time.time()
        if pdu.version not in (SNMPv1, SNMPv2, SNMPv3):
            log.error("unable to handle trap version %d", pdu.version)
            return
        if pdu.transport_data is None:
            log.error("PDU does not contain transport data")
            return

        ip_address, port = _get_addr_and_port_from_packet(pdu)
        if ip_address is None:
            return
        log.debug("received packet from %s on port %s", ip_address, port)
        try:
            self._handler((ip_address, port), pdu, start_time)
        except Exception:
            log.error("unable to handle trap version %s", pdu.version)
        else:
            if pdu.command == netsnmp.CONSTANTS.SNMP_MSG_INFORM:
                self.snmpInform((ip_address, port), pdu)
        finally:
            log.debug("completed handling trap")

    def snmpInform(self, addr, pdu):
        """
        A SNMP trap can request that the trap recipient return back a response.
        """
        try:
            reply = netsnmp.lib.snmp_clone_pdu(ctypes.byref(pdu))
            if not reply:
                log.error("could not clone PDU for INFORM response")
                return
            reply.contents.command = netsnmp.CONSTANTS.SNMP_MSG_RESPONSE
            reply.contents.errstat = 0
            reply.contents.errindex = 0

            # FIXME: might need to add udp6 for IPv6 addresses
            sess = netsnmp.Session(
                peername="%s:%d" % tuple(addr), version=pdu.version
            )
            sess.open()
            try:
                if not netsnmp.lib.snmp_send(sess.sess, reply):
                    netsnmp.lib.snmp_sess_perror(
                        "unable to send inform PDU", self._session.sess
                    )
            finally:
                sess.close()
        finally:
            netsnmp.lib.snmp_free_pdu(reply)


def _pre_parse(session, transport, transport_data, transport_data_length):
    """
    Called before the net-snmp library parses the PDU.
    In the case where a v3 trap comes in with unkwnown credentials,
    net-snmp silently discards the packet. This method gives zentrap a
    way to log that these packets were received to help with
    troubleshooting.
    """
    if log.isEnabledFor(logging.DEBUG):
        ipv6_socket_address = ctypes.cast(
            transport_data, ctypes.POINTER(sockaddr_in6)
        ).contents
        if ipv6_socket_address.family == socket.AF_INET6:
            log.debug(
                "pre_parse: IPv6 %s",
                socket.inet_ntop(socket.AF_INET6, ipv6_socket_address.addr),
            )
        elif ipv6_socket_address.family == socket.AF_INET:
            ipv4_socket_address = ctypes.cast(
                transport_data, ctypes.POINTER(sockaddr_in)
            ).contents
            log.debug(
                "pre_parse: IPv4 %s",
                socket.inet_ntop(socket.AF_INET, ipv4_socket_address.addr),
            )
        else:
            log.debug(
                "pre_parse: unexpected address family: %s",
                ipv6_socket_address.family,
            )
    return 1


def _getPacketIp(addr):
    """
    For IPv4, convert a pointer to 4 bytes to a dotted-ip-address
    For IPv6, convert a pointer to 16 bytes to a canonical IPv6 address.
    """

    def _gen_byte_pairs():
        for left, right in zip(addr[::2], addr[1::2]):
            yield "%.2x%.2x" % (left, right)

    v4_mapped_prefix = [0x00] * 10 + [0xFF] * 2
    if addr[: len(v4_mapped_prefix)] == v4_mapped_prefix:
        ip_address = ".".join(str(i) for i in addr[-4:])
    else:
        try:
            basic_v6_address = ":".join(_gen_byte_pairs())
            ip_address = str(IPAddress(basic_v6_address, 6))
        except ValueError:
            log.warn("The IPv6 address is incorrect: %s", addr[:])
            ip_address = "::"
    return ip_address


def _get_addr_and_port_from_packet(pdu):
    ipv6_socket_address = ctypes.cast(
        pdu.transport_data, ctypes.POINTER(sockaddr_in6)
    ).contents
    if ipv6_socket_address.family == socket.AF_INET6:
        if pdu.transport_data_length < ctypes.sizeof(sockaddr_in6):
            log.error(
                "PDU transport data is too small for sockaddr_in6 struct."
            )
            return (None, None)
        ip_address = _getPacketIp(ipv6_socket_address.addr)
    elif ipv6_socket_address.family == socket.AF_INET:
        if pdu.transport_data_length < ctypes.sizeof(sockaddr_in):
            log.error(
                "PDU transport data is too small for sockaddr_in struct."
            )
            return (None, None)
        ipv4_socket_address = ctypes.cast(
            pdu.transport_data, ctypes.POINTER(sockaddr_in)
        ).contents
        ip_address = ".".join(str(i) for i in ipv4_socket_address.addr)
    else:
        log.error(
            "received a packet with unrecognized network family: %s",
            ipv6_socket_address.family,
        )
        return (None, None)

    port = socket.ntohs(ipv6_socket_address.port)
    return (ip_address, port)
