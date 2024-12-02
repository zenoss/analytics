##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


"""fixIpv6Network

Add an IPv6 network model for tracking IPv6 networks.
"""

import Migrate
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenModel.IpNetwork import IpNetwork
from Products.Zuul.utils import safe_hasattr as hasattr

class fixIpv6Network(Migrate.Step):
    version = Migrate.Version(4,2,70)

    def cutover(self, dmd):
        if hasattr(dmd, 'IPv6Networks'):
            for brain in ICatalogTool(dmd.IPv6Networks).search(IpNetwork):
                try:
                    org = brain.getObject()
                    org.version = 6
                except Exception:
                    pass

# Add a variable so that other scripts can depend on
# this script
fixIpv6NetworkInstance = fixIpv6Network()
