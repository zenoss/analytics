##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
from Products.Zuul.interfaces.tree import ICatalogTool
from Products.Zuul.utils import safe_hasattr as hasattr
import logging
log = logging.getLogger('zen.migrate')

class JobsDelete_4_0(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def cutover(self, dmd):
        jmgr = getattr(dmd, 'JobManager', None)
        if jmgr:
            log.info("Removing old job records")
            for ob in ICatalogTool(dmd.JobManager).search():
                try:
                    if ob.getPath() != '/zport/dmd/JobManager':
                        dmd.global_catalog._catalog.uncatalogObject(ob.getPath())
                except Exception:
                    log.warn("Error removing %s", ob.getPath())
            log.info("Removing old job relationship")
            if hasattr(jmgr, 'jobs'):
                jmgr._delOb('jobs')


jobDelete_4_0 = JobsDelete_4_0()
