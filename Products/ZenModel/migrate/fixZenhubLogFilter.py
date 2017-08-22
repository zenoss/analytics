
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
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION

sm.require("1.0.0")


class FixZenhubLogFilter(Migrate.Step):
    """Correct the LogFilter for /opt/zenoss/log/zenhub.log"""

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = filter(lambda s: s.name == "zenhub", ctx.services)
        log.info("Found %d services named 'zenhub'." % len(services))

        changed = False
        for service in services:
            for logConfig in service.logConfigs:
                if logConfig.path == "/opt/zenoss/log/zenhub.log":
                    if logConfig.filters is None:
                        log.info("Updating logfilter for %s", logConfig.path)
                        logConfig.filters = ["pythondaemon"]
                        changed = True
                    else:
                        log.info("No updates necesary for the logfilter for %s", logConfig.path)

        if changed:
            # Commit our changes.
            ctx.commit()


FixZenhubLogFilter()
