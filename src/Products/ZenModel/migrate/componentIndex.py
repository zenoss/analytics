##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds indexes for fields displayed in the
device list.
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

import Migrate

class NewComponentIndexes(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = devices.componentSearch
        cat = zcat._catalog
        try:
            cat.addIndex('getCollectors', 
                makeCaseInsensitiveKeywordIndex('getCollectors'))
            cat.addIndex('getParentDeviceName', 
                makeCaseInsensitiveFieldIndex('getParentDeviceName'))
            print "Reindexing. This may take some time..."
            zcat.reindexIndex('getCollectors', None)
            zcat.reindexIndex('getParentDeviceName', None)
        except CatalogError:
            pass

NewComponentIndexes()
