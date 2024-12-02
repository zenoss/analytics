##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


#from Products.ZenModel.LinkManager import _create_layer2_catalog

import logging
log = logging.getLogger("zen.migrate")

import sys


class Layer2Catalog(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):  
        """
        # Add the catalog
        try:
            getattr(dmd.ZenLinkManager, 'layer2_catalog')
        except AttributeError:
            #_create_layer2_catalog(dmd.ZenLinkManager)

        # Reindex the interfaces
        print "Indexing interfaces. This may take a while."

        def _update(i):
            if   i % 5000 == 0 and i > 0: print i,
            elif i % 1000 == 0: print '.',
            sys.stdout.flush()

        for i, iface in enumerate(dmd.Devices.getSubComponents("IpInterface")):
            iface.index_object()
            _update(i)
        """
        pass


Layer2Catalog()
