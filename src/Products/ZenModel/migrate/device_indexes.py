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
from Products.ZenUtils.Search import makeFieldIndex, makePathIndex

import Migrate

fieldIndexes = ['id', 'getDeviceIp', 'getDeviceClassPath', 'getProdState']
pathIndexes = ['getPhysicalPath']

class NewDeviceIndexes(Migrate.Step):

    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = devices.deviceSearch
        cat = zcat._catalog
        reindex = False
        for indexName in fieldIndexes:
            try: 
                cat.addIndex(indexName, makeFieldIndex(indexName))
                reindex = True
            except CatalogError:
                pass
        for indexName in pathIndexes:
            try: 
                cat.addIndex(indexName, makePathIndex(indexName))
                reindex = True
            except CatalogError:
                pass
        try: 
            cat.addColumn('id')
            reindex = True
        except CatalogError:
            pass
        if reindex: 
            print "Reindexing. This may take some time..."
            devices.reIndex()

NewDeviceIndexes()
