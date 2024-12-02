##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
Adds the attribute networks_per_device_cache to ZenLinkManager in case it has not already been added
'''

import Migrate
from Products.ZenModel.LinkManager import DeviceNetworksCache

class AddNetworksPerDeviceCache(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        if not hasattr(dmd.ZenLinkManager, 'networks_per_device_cache'):
            dmd.ZenLinkManager.networks_per_device_cache = DeviceNetworksCache()
            l3_catalog = dmd.ZenLinkManager.layer3_catalog
            brains = l3_catalog.searchResults()
            print "Loading {0} links from the layer 3 catalog. This may take some time...".format(len(brains))
            for brain in brains:
                if brain.deviceId and brain.networkId:
                    dmd.ZenLinkManager.add_device_network_to_cache(brain.deviceId, brain.networkId)

AddNetworksPerDeviceCache()
