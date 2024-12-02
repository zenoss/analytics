##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
import Migrate
import zExceptions

import logging
log = logging.getLogger("zen.migrate")

import time

class RebuildPathIndex(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import jobmanager_jobs_delete_4_0
        self.dependencies = [ jobmanager_jobs_delete_4_0.jobDelete_4_0]

    def cutover(self, dmd):
        if getattr(dmd, "_pathReindexed", None) is not None:
            log.info('path has already been reindexed')
            return
        zport = dmd.getPhysicalRoot().zport
        tstart=time.time()
        starttotal = time.time()
        i = 0
        # global catalog
        CHUNK_SIZE = 200 if sys.stdout.isatty() else 25000 # Don't be chatty when logging to a file
        for x in zport.global_catalog():
            i+=1
            try:
                # we updated how ipaddresses and path were stored so re-catalog them
                zport.global_catalog.catalog_object(x.getObject(),x.getPath(),
                                                    idxs=['path', 'ipAddress'],
                                                    update_metadata=False)
            except TypeError:
                # work around for bad data
                log.warning("Unable to index %s " % x.getPath())
            except (KeyError, zExceptions.NotFound):
                zport.global_catalog.uncatalog_object(x.getPath())
            if i % CHUNK_SIZE == 0:
                self.log_progress("rate=%.2f/sec count=%d" %
                                  (CHUNK_SIZE/(time.time()-tstart), i))
                tstart=time.time()
        print
        log.info("Finished total time=%.2f rate=%.2f count=%d",
                time.time()-starttotal, i/(time.time()-starttotal),i)
        dmd._pathReindexed = True


RebuildPathIndex()
