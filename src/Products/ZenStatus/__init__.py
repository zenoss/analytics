##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

__all__ = (
    "CollectionStatistic",
    "nmap",
    "ping",
    "PingCollectionPreferences",
    "PingTask",
)

import collections as _collections

from . import nmap
from . import ping
from .CollectionStatistic import CollectionStatistic
from .PingCollectionPreferences import PingCollectionPreferences
from .PingTask import PingTask

# define a namedtuple to store hop results
TraceHop = _collections.namedtuple("TraceHop", "ip rtt")

del _collections
