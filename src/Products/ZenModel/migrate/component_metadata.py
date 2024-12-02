##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds meta_type metadata to the component catalog
''' 

__version__ = "$Revision$"[11:-2]
        
from Products.ZCatalog.Catalog import CatalogError

import Migrate

class NewComponentMetadata(Migrate.Step):

    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        devices = dmd.getDmdRoot('Devices')
        zcat = devices.componentSearch
        cat = zcat._catalog
        reindex = False
        try: 
            cat.addColumn('meta_type')
            reindex = True
        except CatalogError:
            pass
        if reindex: 
            print "Reindexing. This may take some time..."
            devices.reIndex()

NewComponentMetadata()
