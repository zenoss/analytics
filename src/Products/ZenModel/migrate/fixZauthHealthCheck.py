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
sm.require("1.0.0")


class FixZauthHealthCheck(Migrate.Step):
    """
    Use different curl request to prevent `authentication failed` spam in audit.log
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zauths = filter(lambda s: s.name == "Zauth", ctx.services)
        for zauth in zauths:
            healthChecks = filter(lambda hc: hc.name == "answering", zauth.healthChecks)
            for check in healthChecks:
                check.script = "curl -o /dev/null -w '%{redirect_url}' -s http://localhost:9180/zport/dmd | grep -q acl_users"
                log.info("Updated 'answering' healthcheck.")

        ctx.commit()


FixZauthHealthCheck()
