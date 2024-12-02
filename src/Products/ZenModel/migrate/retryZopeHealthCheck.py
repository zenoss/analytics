##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
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


class RetryZopeHealthCheck(Migrate.Step):
    "Change 'answering' healthcheck to retry a few times on failture"

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zope_services = filter(lambda s: s.name == 'Zope', ctx.services)

        # Update all of the 'answering' healthchecks
        for service in zope_services:
            answeringHealthChecks = filter(lambda healthCheck: healthCheck.name == "answering", service.healthChecks)
            for check in answeringHealthChecks:
                check.script = "curl -o /dev/null --retry 3 --max-time 2 -w '%{redirect_url}' -s http://localhost:9080/zport/dmd | grep -q acl_users"
                check.interval = 15.0
                log.info("Updated 'answering' healthcheck.")

        ctx.commit()

RetryZopeHealthCheck()
