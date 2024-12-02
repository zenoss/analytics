##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
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


class SetZeneventMaxInstances(Migrate.Step):
    """Add `Max = 1` to zeneventserver service"""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = filter(lambda s: s.name == "zeneventserver", ctx.services)
        log.info("Found %d services named 'zeneventserver'." % len(services))

        changed = False
        for service in services:
            if not service.instanceLimits.maximum == 1:
                log.info("Instance max is not 1; setting.")
                service.instanceLimits.maximum = 1
                changed = True
            else:
                log.info("Instance max is already 1; skipping.")

        if changed:
            # Commit our changes.
            ctx.commit()


SetZeneventMaxInstances()
