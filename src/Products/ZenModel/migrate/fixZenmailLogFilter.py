
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration import InstanceLimits

sm.require("1.0.0")


class FixZenmailLogFilter(Migrate.Step):
    """Correct the LogFilter for /opt/zenoss/log/zenmail.log"""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = filter(lambda s: s.name == "zenmail", ctx.services)
        log.info("Found %d services named 'zenmail'." % len(services))

        changed = False
        for service in services:
            for logConfig in service.logConfigs:
                if logConfig.path == "/opt/zenoss/log/zenmail.log":
                    if logConfig.filters[0] != "pythondaemon":
                        log.info("Updating logfilter for %s", logConfig.path)
                        logConfig.filters[0] = "pythondaemon"
                        changed = True
                    else:
                        log.info("No updates necesary for the logfilter for %s", logConfig.path)

        if changed:
            # Commit our changes.
            ctx.commit()


FixZenmailLogFilter()
