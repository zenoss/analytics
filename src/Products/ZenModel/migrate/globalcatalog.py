##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

from zope.component import getUtility
from Products.Zuul.catalog.interfaces import IGlobalCatalogFactory

class GlobalCatalog(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import reindexdevices
        self.dependencies = [reindexdevices.upgradeindices]

    def cutover(self, dmd):
        zport = dmd.getPhysicalRoot().zport

        if getattr(zport, 'global_catalog', None) is None:

            # Create the catalog
            factory = getUtility(IGlobalCatalogFactory)
            factory.create(zport)


GlobalCatalog()
