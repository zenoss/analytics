##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import logging
import time

from twisted.internet import defer
from twisted.internet.protocol import DatagramProtocol

from Products.ZenUtils.IpUtil import asyncNameLookup

log = logging.getLogger("zen.zensyslog.protocol")


class SyslogProtocol(DatagramProtocol):
    """
    Implementation to listen for syslog messages.
    """

    def __init__(self, processor, messagelogger, counters, noreverselookup):
        self._processor = processor
        self._messagelogger = messagelogger
        self._counters = counters
        self._gethostname = (
            defer.succeed if noreverselookup else asyncNameLookup
        )

    def datagramReceived(self, packet, address):
        """
        Consume the network packet

        @param data: syslog message
        @type data: string
        @param address: IP info of the remote device (ipaddr, port)
        @type address: tuple of (string, number)
        """
        if packet == "":
            log.debug("received empty datagram. Discarding.")
            return
        log.debug("received packet from %s -> %s", address, packet)
        self._messagelogger.log(packet, address)

        (ipaddr, port) = address
        d = self._gethostname(ipaddr)
        data = (packet, ipaddr, time.time())
        d.addCallback(self._handle_message, data)
        d.addErrback(self._convert_error, data)

    def doStop(self):
        log.info("stop receiving syslog messages")

    def _convert_error(self, error, data):
        # On failure, use the ip address as the hostname.
        self._handle_message(data[1], data)

    def _handle_message(self, hostname, data):
        """
        Send the resolved address, if possible, and the event via the thread

        @param response: Twisted response
        @type response: Twisted response
        @param data: (msg, ipaddr, rtime)
        @type data: tuple of (string, string, datetime object)
        """
        (packet, ipaddr, rtime) = data
        result = self._processor.process(packet, ipaddr, hostname, rtime)
        if result == "ParserDropped":
            self._counters["eventParserDroppedCount"] += 1
