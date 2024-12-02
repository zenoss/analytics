##############################################################################
#
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""CollectionStatistic
Class that calculates common stats for a collected value.
"""

import logging

from math import fsum, sqrt, pow

log = logging.getLogger("zen.CollectionStatistic")


class CollectionStatistic(object):
    """
    Class that calculates common stats for a collected value.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.start = 0
        self.sent = 0
        self.rcvCount = 0
        self.loss = 0

        self.results = []
        self.rtt = 0
        self.rtt_max = 0.0
        self.rtt_min = 0.0
        self.rtt_avg = 0.0
        self.rtt_stddev = 0.0
        self.rtt_losspct = 0.0

    def logRequest(self):
        self.sent += 1
        raise NotImplementedError

    def logResponse(self, val):
        self.results.append(val)
        self.rcvCount += 1
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
