##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex

log = logging.getLogger( 'zen.migrate' )

def addIndexToCatalog( zCatalog, indexId ):
    if indexId not in zCatalog.indexes():
        cat = zCatalog._catalog
        cat.addIndex( indexId, makeCaseInsensitiveFieldIndex( indexId ) )

class AddTitleOrIdToCatalogs(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        zcat = dmd.Devices.deviceSearch
        addIndexToCatalog( zcat, 'titleOrId' )
        log.info( 'Reindexing devices.  This may take a while...' )
        dmd.Devices.reIndex()


AddTitleOrIdToCatalogs()
