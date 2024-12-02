##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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
from servicemigration import HealthCheck
sm.require("1.0.0")


class AddZenMailHealthCheck(Migrate.Step):
    """Add `service_ready` healthcheck to zenmail service"""

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service_ready_healthcheck = HealthCheck(
            name="service_ready",
            interval=10.0,
            script="echo 'QUIT' | nc -w 10 -C 127.0.0.1 50025 | grep -q '^220 '")

        zenmail_services = filter(lambda s: s.name == "zenmail", ctx.services)
        log.info("Found %i services named 'zenmail'." % len(zenmail_services))
        for zenmail_service in zenmail_services:
            if not filter(lambda c: c.name == 'service_ready', zenmail_service.healthChecks):
                log.info("Service_ready healthcheck not found; adding.")
                zenmail_service.healthChecks.append(service_ready_healthcheck)
            else:
                log.info("Service_ready healthcheck found; skipping.")

        # Commit our changes.
        ctx.commit()


AddZenMailHealthCheck()
