##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


from Products.CMFCore.utils import getToolByName
from Products.ZenUtils.Search import makeMultiPathIndex
from Products.ZCatalog.Catalog import CatalogError

import logging
log = logging.getLogger("zen.migrate")

class DevicePathIndex(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        cat = getToolByName(dmd.Devices, 'deviceSearch')
        try:
            cat._catalog.addIndex('path', makeMultiPathIndex('path'))
        except CatalogError:
            # Index already exists
            pass
        try:
            cat.addColumn('path')
        except CatalogError:
            # Column exists
            pass

devicepathindex = DevicePathIndex()
