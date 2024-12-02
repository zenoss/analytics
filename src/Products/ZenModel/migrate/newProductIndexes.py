##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds additional indexes and metadata to the existing
productSearch catalog. It is primarily intended to speed up the performance of
a device's Edit tab on systems with a large number of products.
''' 

__version__ = "$Revision$"[11:-2]

import logging
 
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ManagableIndex import FieldIndex

import Migrate

log = logging.getLogger('zen.migrate')

class NewProductIndexes(Migrate.Step):

    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        manufacturers = dmd.getDmdRoot('Manufacturers')
        zcat = manufacturers.productSearch
        cat = zcat._catalog
        try:
            cat.addIndex('getManufacturerName',
                makeCaseInsensitiveFieldIndex('getManufacturerName'))
            cat.addIndex('meta_type',
                makeCaseInsensitiveFieldIndex('meta_type'))
            cat.addIndex('isOS', FieldIndex('isOS'))

            zcat.addColumn('id')

            log.info("Reindexing products. This may take some time...")
            manufacturers.reIndex()
        except CatalogError:
            pass

NewProductIndexes()
