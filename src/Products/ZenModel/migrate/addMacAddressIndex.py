##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys
import time
import Migrate

import logging
log = logging.getLogger('zen.migrate')

from Products.AdvancedQuery import In
from Products.Zuul.interfaces import ICatalogTool
from Products.ZCatalog.Catalog import CatalogError
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex

class MacAddressIndex(Migrate.Step):
    version = Migrate.Version(5, 0, 0)

    def cutover(self, dmd):
        cat = dmd.zport.global_catalog

        try:
            cat.addIndex('macAddresses',
                makeCaseInsensitiveKeywordIndex('macAddresses'))

            if hasattr(cat, 'applyConfig'):
                cat.applyConfig()
        except CatalogError as e:
            if hasattr(dmd.zport, '_hasMacIndex'):
                return

            print "Reindexing.  This may take some time..."
            starttotal = time.time()
            tstart = time.time()
            i = 0
            CHUNK_SIZE = 200 if sys.stdout.isatty() else 25000 # Don't be chatty when logging to file

            fqdns = ('Products.ZenModel.Device.Device',
                     'Products.ZenModel.IpInterface.IpInterface',
                     'ZenPacks.zenoss.ZenVMware.VMwareGuest.VMwareGuest',
                     'ZenPacks.zenoss.vCloud.VM.VM',)

            results = ICatalogTool(dmd).search(fqdns[1:])
            for brain in results.results:
                i += 1

                try:
                    obj = brain.getObject()
                except Exception as e:
                    log.exception("Cannot find object at path %s", brain.getPath())
                    cat.uncatalog_object(brain.getPath())
                    continue

                obj.index_object()
                cat.catalog_object(obj)
                log.debug("Catalogued object %s", obj.absolute_url_path())

                if i % CHUNK_SIZE == 0:
                    self.log_progress("rate=%.2f/sec count=%d" %
                        (CHUNK_SIZE/(time.time() - tstart), i))
                    tstart = time.time()

            results = ICatalogTool(dmd).search(fqdns)
            for brain in results.results:
                i += 1

                try:
                    obj = brain.getObject()
                except Exception as e:
                    log.exception("Cannot find object at path %s", brain.getPath())
                    cat.uncatalog_object(brain.getPath())
                    continue

                cat.catalog_object(obj)
                log.debug("Catalogued object %s", obj.absolute_url_path())

                if i % CHUNK_SIZE == 0:
                    self.log_progress("rate=%.2f/sec count=%d" %
                        (CHUNK_SIZE/(time.time() - tstart), i))
                    tstart = time.time()

            print
            log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal), i)
            setattr(dmd.zport, '_hasMacIndex', True)

MacAddressIndex()
