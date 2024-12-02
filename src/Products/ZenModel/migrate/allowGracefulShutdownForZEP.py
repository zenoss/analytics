##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
import servicemigration as sm
import Migrate


log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class AllowGracefulShutdownForZEP(Migrate.Step):
    """Modify zeneventserver's service def for graceful shutdown."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service = next(
            (s for s in ctx.services if s.name == "zeneventserver"), None,
        )
        if service is None:
            log.error("Unable to find the 'zeneventserver' service")
            return

        service.startup = "/opt/zenoss/bin/zeneventserver run_quiet"
        service.environment = [
            "DEFAULT_ZEP_JVM_ARGS='-server -Xmx{{.RAMCommitment}}'"
        ]
        service.runAs = "zenoss"
        ctx.commit()
        log.info("Updated the 'zeneventserver' service")


AllowGracefulShutdownForZEP()
