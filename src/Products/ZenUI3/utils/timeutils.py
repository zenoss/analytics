##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import math
import time

from decimal import Decimal


def readable_time(seconds, precision=1):
    """
    Convert some number of seconds into a human-readable string.

    @param t: The number of seconds to convert
    @type t: int
    @param precision: The maximum number of time units to include.
    @type t: int
    @rtype: str

        >>> readable_time(None)
        '0 seconds'
        >>> readable_time(0)
        '0 seconds'
        >>> readable_time(0.12)
        '0 seconds'
        >>> readable_time(1)
        '1 second'
        >>> readable_time(1.5)
        '1 second'
        >>> readable_time(60)
        '1 minute'
        >>> readable_time(60*60*3+12)
        '3 hours'
        >>> readable_time(60*60*3+12, 2)
        '3 hours 12 seconds'

    """
    if seconds is None:
        return "0 seconds"
    remaining = abs(seconds)
    if remaining < 1:
        return "0 seconds"

    names = ("year", "month", "week", "day", "hour", "minute", "second")
    mults = (
        60 * 60 * 24 * 365,
        60 * 60 * 24 * 30,
        60 * 60 * 24 * 7,
        60 * 60 * 24,
        60 * 60,
        60,
        1,
    )
    result = []
    for name, div in zip(names, mults):
        num = Decimal(str(math.floor(remaining / div)))
        remaining -= int(num) * div
        num = int(num)
        if num:
            result.append("%d %s%s" % (num, name, num > 1 and "s" or ""))
        if len(result) == precision:
            break
    return " ".join(result)


def relative_time(t, precision=1, cmptime=None):
    """
    Return a human-readable string describing time relative to C{cmptime}
    (defaulted to now).

    @param t: The time to convert, in seconds since the epoch.
    @type t: int
    @param precision: The maximum number of time units to include.
    @type t: int
    @param cmptime: The time from which to compute the difference, in seconds
    since the epoch
    @type cmptime: int
    @rtype: str

        >>> relative_time(time.time() - 60*10)
        '10 minutes ago'
        >>> relative_time(time.time() - 60*10-3, precision=2)
        '10 minutes 3 seconds ago'
        >>> relative_time(time.time() - 60*60*24*10, precision=2)
        '1 week 3 days ago'
        >>> relative_time(time.time() - 60*60*24*365-1, precision=2)
        '1 year 1 second ago'
        >>> relative_time(time.time() + 1 + 60*60*24*7*2) # Add 1 for rounding
        'in 2 weeks'

    """
    if cmptime is None:
        cmptime = time.time()
    seconds = Decimal(str(t - cmptime))
    result = readable_time(seconds, precision)
    if seconds < 0:
        result += " ago"
    else:
        result = "in " + result
    return result
