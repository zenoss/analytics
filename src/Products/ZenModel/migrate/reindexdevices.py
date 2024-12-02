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
log = logging.getLogger("zen.migrate")

from Products.ZenUtils.Search import makePathIndex, makeMultiPathIndex

class UpgradeMultiPathIndices(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def cutover(self, dmd):
        idx = dmd.Devices.deviceSearch._catalog.indexes['path']
        idx_parents = getattr(idx, '_index_parents', None)
        if idx_parents is None:
            dmd.Devices.deviceSearch.delIndex('path')
            dmd.Devices.deviceSearch._catalog.addIndex('path', 
                    makeMultiPathIndex('path'))
            # grab each device and manually reindex it
            log.info( 'Reindexing devices.  This may take a while ...' )
            for device in dmd.Devices.getSubDevices_recursive():
                dmd.Devices.deviceSearch.catalog_object(device, idxs=('path',))
                
        idx = dmd.searchRRDTemplates._catalog.indexes['getPhysicalPath']
        if not idx.__class__.__name__=='ExtendedPathIndex':
            templates = dmd.searchRRDTemplates()
            dmd.searchRRDTemplates.delIndex('getPhysicalPath')
            dmd.searchRRDTemplates._catalog.addIndex('getPhysicalPath', 
                    makePathIndex('getPhysicalPath'))
            for template in templates:
                dmd.searchRRDTemplates.catalog_object(template.getObject(), idxs=('getPhysicalPath',))
upgradeindices = UpgradeMultiPathIndices()
