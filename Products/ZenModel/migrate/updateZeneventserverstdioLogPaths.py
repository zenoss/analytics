##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm
from Products.ZenUtils.path import zenPath

log = logging.getLogger("zen.migrate")
sm.require("1.1.10")

class UpdateZeneventserverstdioLogPaths(Migrate.Step):
    """
    Fix the rabbit log file location so Kibana picks them up.
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        svcs = filter(lambda s: "zeneventserver" in s.name, ctx.services)
        log.info("Found {0} services with 'zeneventserver' in their service path".format(len(svcs)))
        changed = False
        for svc in svcs:
            for logConfig in svc.logConfigs:
                if logConfig.logType == "zeneventserver_stdio" and "stdio*" in logConfig.path:
                    log.info("Updating zeneventserver_stdio log file location")
                    logConfig.path = "/opt/zenoss/log/zeneventserver-stdio.[0-9]*_[0-9]*_[0-9]*.log"
                    changed = True
        if changed:
            # Commit our changes.
            ctx.commit()

UpdateZeneventserverstdioLogPaths()
