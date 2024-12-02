##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""PingResult

Utilities to parse nmap output and represent results.
"""

import logging
import time

from zope import interface

from Products.ZenStatus import interfaces

_STATE_TO_STRING_MAP = {True: "up", False: "down"}
_NAN = float("nan")

log = logging.getLogger("zen.zenping.cmdping.PingResult")


@interface.implementer(interfaces.IPingResult)
class PingResult(object):
    """
    Model of an ping/traceroute result.
    """

    def __init__(
        self,
        ip,
        exitCode,
        pingOutput,
        timestamp=None,
    ):
        """Ping output container."""
        if timestamp is None:
            self._timestamp = time.time()
        else:
            self._timestamp = timestamp
        self._address = ip
        self._trace = tuple()
        if exitCode:
            self._isUp = False
        else:
            self._isUp = True
        self._rtt = _NAN
        self._mdev = _NAN
        if exitCode == 0:
            parsedOutput = self._parse(pingOutput)
            if parsedOutput is not None:
                (min, avg, max, mdev) = parsedOutput
                self._rtt = avg
                self._mdev = mdev

    def _parse(self, output):
        try:
            lastLine = output.splitlines(False)[-1]
            valueList = lastLine.split("=")[1].strip()
            min, avg, max, mdev = [
                float(x) for x in valueList.split()[0].split("/")
            ]
        except Exception as ex:
            log.exception(ex)
            log.error("Could not parse ping output.")
            log.debug("Ping output %s: %s", self._address, output)
            return None
        return (min, avg, max, mdev)

    @property
    def timestamp(self):
        """Timestamp of when ping was returned (seconds since epoch)."""
        return self._timestamp

    @property
    def address(self):
        """Address of the host"""
        return self._address

    @property
    def trace(self):
        """traceroute of the host"""
        return tuple(self._trace)

    def getStatusString(self):
        """status string: up or down"""
        return _STATE_TO_STRING_MAP[self._isUp]

    def __repr__(self):
        return "PingResult [%s, %s]" % (self._address, self.getStatusString())

    @property
    def isUp(self):
        """true if host is up, false if host is down"""
        return self._isUp

    @property
    def rtt(self):
        """round trip time aka ping time aka rtt; nan if host was down"""
        return self._rtt

    @property
    def variance(self):
        """variance of the rtt; nan if host was down"""
        return self._mdev * self._mdev

    @property
    def stdDeviation(self):
        """standard deviation of the rtt; nan if host was down"""
        return self._mdev
