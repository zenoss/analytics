##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import errno
import logging
import socket
import sys

import ctypes as c  # Magical interfacing with C code

from pynetsnmp import netsnmp

# Version codes from the PDU
SNMPv1 = netsnmp.SNMP_VERSION_1
SNMPv2 = netsnmp.SNMP_VERSION_2c
SNMPv3 = netsnmp.SNMP_VERSION_3

log = logging.getLogger("zen.zentrap")

# This is what struct sockaddr_in {} looks like
family = [("family", c.c_ushort)]
if sys.platform == "darwin":
    family = [("len", c.c_ubyte), ("family", c.c_ubyte)]


class sockaddr_in(c.Structure):
    _fields_ = family + [
        ("port", c.c_ubyte * 2),  # need to decode from net-byte-order
        ("addr", c.c_ubyte * 4),
    ]


class sockaddr_in6(c.Structure):
    _fields_ = family + [
        ("port", c.c_ushort),  # need to decode from net-byte-order
        ("flow", c.c_ubyte * 4),
        ("addr", c.c_ubyte * 16),
        ("scope_id", c.c_ubyte * 4),
    ]


pre_parse_factory = c.CFUNCTYPE(
    c.c_int,
    c.POINTER(netsnmp.netsnmp_session),
    c.POINTER(netsnmp.netsnmp_transport),
    c.c_void_p,
    c.c_int,
)

# teach python that the return type of snmp_clone_pdu is a pdu pointer
netsnmp.lib.snmp_clone_pdu.restype = netsnmp.netsnmp_pdu_p


def ipv6_is_enabled():
    """test if ipv6 is enabled"""
    # hack for ZEN-12088 - TODO: remove next line
    return False
    try:
        socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
    except socket.error as e:
        if e.errno == errno.EAFNOSUPPORT:
            return False
        raise
    return True


class FakePacket(object):
    """
    A fake object to make packet replaying feasible.
    """

    def __init__(self):
        self.fake = True
