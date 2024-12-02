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


class DisableZproxyAccessLog(Migrate.Step):
    "Disable zproxy nginx access logging by default"

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy_service = ctx.getTopService()
        if not zproxy_service:
            log.info("No top service found, skipping")
            return

        # Update zproxy-nginx.conf.
        cfs = filter(lambda f: f.name == "/opt/zenoss/zproxy/conf/zproxy-nginx.conf",
                     zproxy_service.originalConfigs + zproxy_service.configFiles)
        log.info("Found %i config files named '/opt/zenoss/zproxy/conf/zproxy-nginx.conf'." % len(cfs))
        for cf in cfs:
            cf.content = re.sub(
                r'^(\s*access_log)\s+/opt/zenoss/zproxy/logs/access.log;',
                r'\1 off;',
                cf.content, 0, re.MULTILINE)
            log.info("Disabled zproxy nginx access logging")

        # Commit our changes.
        ctx.commit()


DisableZproxyAccessLog()
