##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
The name of the CentralQuery healthcheck has a typo as 'anwering'.
This renames these typos to the correct spelling.
"""

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class FixCentralQueryHealthCheckTypo(Migrate.Step):
    "Fix CentralQuery healthcheck typo"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        centralqueries = filter(lambda s: s.name == "CentralQuery", ctx.services)
        if not centralqueries:
            log.info("Couldn't find CentralQuery service, skipping.")
            return
        log.info("Found CentralQuery service.")

        # Locate the health check typos.
        commit = False
        for service in centralqueries:
            typoHealthChecks = filter(lambda healthCheck: healthCheck.name == "anwering", service.healthChecks)
            typos = len(typoHealthChecks)
            if typos > 0:
                log.info("Found %i healthcheck typo in service: %s" % (typos, service.name))
                for healthCheck in typoHealthChecks:
                    healthCheck.name = "answering"
                    log.info("Updated healthcheck name.")
                    commit = True

        if commit:
            log.info("Committing changes.")
            ctx.commit()


FixCentralQueryHealthCheckTypo()
