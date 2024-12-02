##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class ReindexIpAddressNetworkIds(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for brain in dmd.ZenLinkManager.layer3_catalog():
            try:
                ob = brain.getObject()
                ob.index_object()
            except Exception:
                pass

ReindexIpAddressNetworkIds()
