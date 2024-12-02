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

import time
import logging

from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex, makeCaseSensitiveKeywordIndex\
    ,makeCaseSensitiveFieldIndex, makeMultiPathIndex

import Migrate
fieldIndexes = ['getInterfaceName', 'getDeviceName',
                'getInterfaceDescription', 'getInterfaceMacAddress', ]

log = logging.getLogger("zen.migrate")


class IpSearchCatalogUpdate(Migrate.Step):

    version = Migrate.Version(4, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import addIpv6Network
        self.dependencies = [addIpv6Network.addIpv6NetworkInstance]

    def updateNetworkCatalog(self, zcat):
        idxs = []
        # field indexes
        for indexName in fieldIndexes:
            try:
                zcat._catalog.addIndex(indexName, makeCaseInsensitiveFieldIndex(indexName))
                idxs.append(indexName)
            except CatalogError:
                pass
        try:
            zcat._catalog.addIndex('ipAddressAsInt',  makeCaseSensitiveFieldIndex('ipAddressAsInt'))
            idxs.append(indexName)
        except CatalogError:
            pass

        # permissions
        try:
            zcat._catalog.addIndex('allowedRolesAndUsers', makeCaseSensitiveKeywordIndex('allowedRolesAndUsers'))
            idxs.append('allowedRolesAndUsers')
        except CatalogError:
            pass
        # path index
        try:
            zcat._catalog.addIndex('path', makeMultiPathIndex('path'))
            idxs.append('path')
        except CatalogError:
            pass

        # json in the meta data
        try:
            zcat.addColumn('details')
        except CatalogError:
            pass

        i = 0
        tstart=time.time()
        starttotal = time.time()
        for brain in zcat():
            obj = brain.getObject()
            # we don't want to reindex the links on migrate so explicitly index
            # from the catalog
            obj.index_object(idxs=idxs)
            i+=1
            if i % 200 == 0:
                log.info("rate=%.2f/sec count=%d", 200/(time.time()-tstart), i)
                tstart=time.time()
        log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal),i)

    def cutover(self, dmd):
        networks = dmd.getDmdRoot('Networks')

        log.info('Updating Ipv4 Catalog')
        zcat = networks.ipSearch
        self.updateNetworkCatalog(zcat)

        if hasattr(dmd, 'IPv6Networks'):
            log.info('Updating Ipv6 Catalog')
            zcat = dmd.IPv6Networks.ipSearch
            self.updateNetworkCatalog(zcat)

IpSearchCatalogUpdate()
