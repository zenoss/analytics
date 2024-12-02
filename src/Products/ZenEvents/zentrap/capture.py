##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import abc
import cPickle
import logging

from optparse import OptionValueError

import six

from pynetsnmp import netsnmp

from .net import FakePacket, SNMPv1

log = logging.getLogger("zen.zentrap.capture")


@six.add_metaclass(abc.ABCMeta)
class PacketCapture(object):
    """
    Capture raw network packets.
    """

    @staticmethod
    def add_options(parser):
        parser.add_option(
            "--captureFilePrefix",
            dest="captureFilePrefix",
            action="callback",
            callback=_validate_capturefileprefix,
            default=None,
            help="Directory and filename to use as a template "
            "to store captured raw trap packets.",
        )
        parser.add_option(
            "--captureAll",
            dest="captureAll",
            action="callback",
            callback=_handle_captureall,
            default=False,
            help="Capture all packets.",
        )
        parser.add_option(
            "--captureIps",
            dest="captureIps",
            action="callback",
            callback=_handle_captureips,
            default="",
            help="Comma-separated list of IP addresses to capture.",
        )

    @classmethod
    def from_options(cls, options):
        """
        Returns a PacketCapture object if the `captureFilePrefix` attribute
        of the `options` parameter is not empty.
        """
        if options.captureFilePrefix:
            if options.captureIps or options.captureAll:
                return cls(
                    options.replayFilePrefix,
                    options.captureAll,
                    options.captureIps,
                )
            else:
                log.warning(
                    "ignoring --captureFilePrefix because neither "
                    "--captureAll nor --captureIps was specified"
                )

    def __init__(self, fileprefix, allips, ips):
        self._fileprefix = fileprefix
        self._filecount = 0
        if allips:
            self._ips = None
            self._include = lambda x: True
        else:
            self._ips = tuple(ips.split(","))
            self._include = lambda x: x in self._ips

    @property
    def include(self):  # () -> True | Tuple(str)
        """
        Returns what packets are captured.

        Returns True to indicate all packets are captured.

        Returns a tuple of IP address strings indicating that only packets
        from the given IP addesses are captured.
        """
        return self._ips if self._ips else True

    @abc.abstractmethod
    def to_pickleable(self, *data):
        """
        Returns a pickleable object.

        The pickleable object should contain some form of the content
        provided by the `data` argument.
        """

    def capture(self, hostname, *data):
        """
        Store the raw packet for later examination and troubleshooting.

        @param hostname: packet-sending host's name or IP address
        @type hostname: string
        @param data: raw packet and other necessary arguments
        @type data: List[Any]
        """
        if not self._include(hostname):
            log.debug("ignored packet  source=%s", hostname)
            return

        name = "%s-%s-%d" % (self._fileprefix, hostname, self._filecount)
        try:
            serializable = self.to_pickleable(*data)
            serialized = cPickle.dumps(serializable, cPickle.HIGHEST_PROTOCOL)
            with open(name, "wb") as fp:
                fp.write(serialized)
            self._filecount += 1
            log.debug("captured packet  source=%s", hostname)
        except Exception:
            log.exception(
                "failed to capture packet  source=%s file=%s", hostname, name
            )


def _validate_capturefileprefix(option, optstr, value, parser):
    if getattr(parser.values, "replayFilePrefix", None):
        raise OptionValueError(
            "can't use --captureFilePrefix with --replayFilePrefix"
        )
    setattr(parser.values, option.dest, value)


def _handle_captureall(option, optstr, value, parser):
    if getattr(parser.values, "captureIps", None):
        raise OptionValueError("can't use --captureAll with --captureIps")
    setattr(parser.values, option.dest, True)


def _handle_captureips(option, optstr, value, parser):
    if getattr(parser.values, "captureAll", None):
        raise OptionValueError("can't use --captureIps with --captureAll")
    setattr(parser.values, option.dest, value)


class Capture(PacketCapture):
    """
    Wraps a TrapHandler to capture packets.
    """

    @classmethod
    def wrap_handler(cls, options, handler):
        capture = cls.from_options(options)
        if capture:
            capture._handler = handler
        return capture
        
    def __call__(self, addr, pdu, starttime):
        self.capture(addr[0], addr, pdu)
        self._handler(addr, pdu, starttime)

    def to_pickleable(self, addr, pdu):
        """
        Store the raw packet for later examination and troubleshooting.

        @param addr: packet-sending host's IP address and port
        @type addr: (string, number)
        @param pdu: raw packet
        @type pdu: binary
        @return: Python FakePacket object
        @rtype: Python FakePacket object
        """
        packet = FakePacket()
        packet.version = pdu.version
        packet.host = addr[0]
        packet.port = addr[1]
        packet.variables = netsnmp.getResult(pdu, log)
        packet.community = ""
        packet.enterprise_length = pdu.enterprise_length

        # Here's where we start to encounter differences between packet types
        if pdu.version == SNMPv1:
            # SNMPv1 can't be received via IPv6
            packet.agent_addr = [pdu.agent_addr[i] for i in range(4)]
            packet.trap_type = pdu.trap_type
            packet.specific_type = pdu.specific_type
            packet.enterprise = self._handler.getEnterpriseString(pdu)
            packet.community = self._handler.getCommunity(pdu)

        return packet
