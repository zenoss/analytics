##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
Create the networks cache for each Network root
'''

import Migrate
import logging

log = logging.getLogger("zen.migrate")


class createNetworksCache(Migrate.Step):

    version = Migrate.Version(200, 0, 1)

    def cutover(self, dmd):
        for network_root in [ dmd.Networks, dmd.IPv6Networks ]:
            if not hasattr(network_root, network_root.NETWORK_CACHE_ATTR):
                log.info("Initializing network cache for {}".format(network_root.getPrimaryUrlPath()))
                network_root.initialize_network_cache(network_root)


createNetworksCache()
