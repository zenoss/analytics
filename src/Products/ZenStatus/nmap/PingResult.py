##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function


"""PingResult

Utilities to parse nmap output and represent results.
"""

import logging
import math

from traceback import format_exc

from lxml import etree
from zope import interface

from Products.ZenStatus import interfaces, TraceHop

log = logging.getLogger("zen.nmap")

_STATE_TO_STRING_MAP = {True: "up", False: "down"}
_NAN = float("nan")
_NO_TRACE = tuple()


def parseNmapXml(input):
    """
    Parse the XML output of nmap and return a list PingResults.
    """
    results = []
    parseTree = etree.parse(input)
    for hostTree in parseTree.xpath("/nmaprun/host"):
        result = PingResult.createNmapResult(hostTree)
        results.append(result)
    return results


def parseNmapXmlToDict(input):
    """
    Parse the XML output of nmap and return a dict of PingResults indexed
    by IP.
    """
    rdict = {}
    for result in parseNmapXml(input):
        rdict[result.address] = result
    return rdict


class PingResult(object):
    """
    Model of an nmap ping/traceroute result.
    """

    interface.implements(interfaces.IPingResult)

    @staticmethod
    def createNmapResult(hostTree):
        """
        Contruct an PingResult from an XML parse tree for a host entry.
        """
        if getattr(hostTree, "xpath", None) is None:
            raise ValueError("hostTree must be of lxml.etree.Element type")
        pr = PingResult("unknown")
        pr._address = pr._parseAddress(hostTree)
        pr._timestamp = pr._parseTimestamp(hostTree)
        pr._isUp, reason = pr._parseState(hostTree)
        if reason == "localhost-response":
            pr._rtt, pr._rttVariace = (0, 0)
        else:
            try:
                pr._rtt, pr._rttVariance = pr._parseTimes(hostTree)
            except Exception as ex:
                traceback = format_exc()
                log.debug("Error parsing times %s %s ", ex, traceback)
                pr._rtt, pr._rttVariace = (_NAN, _NAN)
        try:
            pr._trace = pr._parseTraceroute(hostTree)
        except Exception as ex:
            traceback = format_exc()
            log.debug("Error parsing trace routes %s %s ", ex, traceback)
            pr._trace = _NO_TRACE
        return pr

    def __init__(
        self,
        address,
        timestamp=None,
        isUp=False,
        rtt=_NAN,
        stddev=_NAN,
        trace=_NO_TRACE,
    ):
        self._address = address
        self._timestamp = timestamp
        self._isUp = isUp
        self._rtt = rtt
        self._rttVariance = stddev * stddev
        self._trace = trace

    def _parseTimestamp(self, hostTree):
        """
        Extract timestamp if it exists.
        """
        try:
            timestamp = None
            starttime = hostTree.attrib.get("starttime", None)
            if starttime is not None:
                timestamp = int(starttime)
        except KeyError:
            return None
        except Exception as ex:
            traceback = format_exc()
            log.debug("Error parsing timestamp %s %s ", ex, traceback)
        return timestamp

    def _parseTimes(self, hostTree):
        """
        Extract round trip time from the hostTree.
        """
        times = hostTree.xpath("times")
        if len(times) != 1:
            raise ValueError("no times found for hostTree")
        timesNode = times[0]
        rtt = timesNode.attrib["srtt"]
        rtt = float(rtt) / 1000.0  # given in micro sec, convert to millisecs
        rttVariance = timesNode.attrib["rttvar"]
        rttVariance = float(rttVariance) / 1000.0
        return (rtt, rttVariance)

    def _parseAddress(self, hostTree):
        """
        Extract the address (ip) from the hostTree.
        """

        addressNodes = hostTree.xpath("address[@addrtype='ipv4']")
        if len(addressNodes) != 1:
            addressNodes = hostTree.xpath("address[@addrtype='ipv6']")
            if len(addressNodes) != 1:
                raise ValueError("hostTree does not have address node")
        addressNode = addressNodes[0]
        address = addressNode.attrib["addr"]
        return address

    def _parseState(self, hostTree):
        """
        Extract the host status from hostTree: return True if up,
        False if down.
        """
        statusNodes = hostTree.xpath("status")
        if len(statusNodes) != 1:
            raise ValueError("hostTree does not have status node")
        statusNode = statusNodes[0]
        state = statusNode.attrib["state"]
        isUp = state.lower() == "up"
        reason = statusNode.attrib.get("reason", "unknown")
        return (isUp, reason)

    def _parseTraceroute(self, hostTree):
        """
        Extract the traceroute hops from hostTree in to a list that
        preserves the hop order and saves the hop rtt.
        """
        hops = []
        traceNodes = hostTree.xpath("trace")
        if len(traceNodes) != 1:
            return tuple()  # no traceroute info in output file
        traceNode = traceNodes[0]
        hopNodes = traceNode.xpath("hop")
        if len(hopNodes) < 1:
            raise ValueError("hostTree does not have a trace/hop nodes")
        for hopNode in hopNodes:
            ipaddr = hopNode.attrib["ipaddr"]
            rtt = float(hopNode.attrib["rtt"])
            hops.append(TraceHop(ip=ipaddr, rtt=rtt))
        return hops

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
        return self._rttVariance

    @property
    def stddev(self):
        """standard deviation of the rtt; nan if host was down"""
        math.sqrt(self._rttVariance)


if __name__ == "__main__":

    import os.path

    nmap_testfile = (
        os.path.dirname(os.path.realpath(__file__)) + "/../tests/nmap_ping.xml"
    )
    results = parseNmapXml(nmap_testfile)
    for result in results:
        print(result)
        for hop in result.trace:
            print("  ->", hop)
