##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from .Uname_A import Uname_A
from .Unix_df_k import Unix_df_k

from .Linux_netstat_an import Linux_netstat_an
from .Linux_netstat_rn import Linux_netstat_rn
from .Linux_ifconfig import Linux_ifconfig

from .CiscoDhcpHelperAddress import CiscoDhcpHelperAddress
from .CiscoShowHardware import CiscoShowHardware


def initCommandParsers(dataCollector):
    dataCollector.addCommandParser(Uname_A)
    dataCollector.addCommandParser(Unix_df_k)

    dataCollector.addCommandParser(Linux_netstat_an)
    dataCollector.addCommandParser(Linux_netstat_rn)
    dataCollector.addCommandParser(Linux_ifconfig)

    dataCollector.addCommandParser(CiscoDhcpHelperAddress)
    dataCollector.addCommandParser(CiscoShowHardware)
