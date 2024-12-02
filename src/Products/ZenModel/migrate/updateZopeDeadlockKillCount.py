##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.0.0")


class UpdateZopeDeadlockKillCount(Migrate.Step):
    """
    Update the deadlock healthcheck to all of the zopes.
    """

    version = Migrate.Version(200, 4, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zopes = filter(lambda s: s.name.lower() in ["zope", "zauth", "zenapi", "zendebug", "zenreports"], ctx.services)
        log.info("Found %i Zope services." % len(zopes))
        for z in zopes:
            deadlockChecks = filter(lambda healthCheck: healthCheck.name == "deadlock_check", z.healthChecks)
            if not deadlockChecks:
                log.warn("Unable to find the zope deadlock healthcheck")
                continue
            else:
                for check in deadlockChecks:
                    check.kill_count_limit = 5		 
        ctx.commit()


UpdateZopeDeadlockKillCount()
