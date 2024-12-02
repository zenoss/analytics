##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__ = """IPv6Network

Add an IPv6 network model for tracking IPv6 networks.
"""

import Migrate
from Products.ZenModel.IpNetwork import manage_addIpNetwork
from Products.Zuul.utils import safe_hasattr as hasattr

class addIpv6Network(Migrate.Step):
    version = Migrate.Version(4,0,0)

    def cutover(self, dmd):
        if not hasattr(dmd, 'IPv6Networks'):
            manage_addIpNetwork(dmd, "IPv6Networks", netmask=64, version=6)

# Add a variable so that other scripts can depend on
# this script
addIpv6NetworkInstance = addIpv6Network()
