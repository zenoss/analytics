##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


from Products.ZenModel.LinkManager import manage_addLinkManager

import logging
log = logging.getLogger("zen.migrate")

class NetworkIndexes(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        try:
            getattr(dmd.ZenLinkManager, 'layer3_catalog')
        except AttributeError:
            try:
                dmd.manage_delObjects('ZenLinkManager')
            except AttributeError:
                pass
            manage_addLinkManager(dmd)


networkindexes = NetworkIndexes()
