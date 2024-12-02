##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""PingJob
Class that contains the information about pinging an individual IP address.
"""

import logging
import socket

from math import fsum, sqrt, pow

from twisted.internet import defer

log = logging.getLogger("zen.PingJob")


class PingJob(object):
    """
    Class representing a single target to be pinged.
    """

    def __init__(
        self,
        ipaddr,
        hostname="",
        status=0,
        ttl=60,
        maxtries=2,
        sampleSize=1,
        iface="",
    ):
        self.ipaddr = ipaddr
        self.iface = iface
        self.hostname = hostname
        self._ttl = ttl
        self.status = status
        self.maxtries = maxtries
        self.sampleSize = sampleSize
        self.points = []  # For storing datapoints

        self.family, self._sockaddr = self._getaddrinfo()
        self.address = self._sockaddr[0]
        self.ipVersion = 4 if self.family == socket.AF_INET else 6
        self.data_size = 56

        self.reset()

    def _getaddrinfo(self):
        family = socket.AF_UNSPEC
        for info in socket.getaddrinfo(self.ipaddr, None, socket.AF_UNSPEC):
            family = info[0]
            sockaddr = info[-1]
            if family in (socket.AF_INET, socket.AF_INET6):
                return family, sockaddr

        raise StandardError(
            "Could not resolve IP address '%s' on %s for family %s"
            % (self.ipaddr, self.hostname, family)
        )

    def reset(self):
        self.deferred = defer.Deferred()
        self.start = 0
        self.sent = 0
        self.rcvCount = 0
        self.loss = 0
        self.message = ""
        self.severity = 5
        self.inprocess = False

        self.results = []
        self.rtt = 0
        self.rtt_max = 0.0
        self.rtt_min = 0.0
        self.rtt_avg = 0.0
        self.rtt_stddev = 0.0
        self.rtt_losspct = 0.0

        self._lastSequenceNumber = 0

    def calculateStatistics(self):
        n = len(self.results)
        if n == 0:
            return

        elif n == 1:
            self.rtt_avg = self.rtt
            self.rtt_max = self.rtt
            self.rtt_min = self.rtt
            self.rtt_stddev = 0.0
            return

        total = fsum(self.results)
        self.rtt_avg = total / n
        self.rtt_stddev = self.stdDev(self.rtt_avg)

        self.rtt_min = min(self.results)
        self.rtt_max = max(self.results)

        self.rtt_losspct = ((self.sent - self.loss) / self.sent) * 100

    def stdDev(self, avg):
        """
        Calculate the sample standard deviation.
        """
        n = len(self.results)
        if n < 1:
            return 0
        # sum of squared differences from the average
        total = fsum(map(lambda x: pow(x - avg, 2), self.results))
        # Bessel's correction uses n - 1 rather than n
        return sqrt(total / (n - 1))

    def pingArgs(self):
        self._lastSequenceNumber += 1
        echo_kwargs = dict(
            sequence=self._lastSequenceNumber,
            data_size=self.data_size,
        )
        socket_kwargs = dict(
            ttl=self._ttl,
        )
        return self.family, self._sockaddr, echo_kwargs, socket_kwargs

    def __str__(self):
        return "%s %s" % (self.hostname, self.ipaddr)
