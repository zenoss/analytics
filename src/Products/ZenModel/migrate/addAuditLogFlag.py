##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm

sm.require("1.1.7")

class AddAuditLogFlag(Migrate.Step):
    """ Add boolean flag to indicate which logs are audit logs."""

    version = Migrate.Version(114, 0, 0)

    def cutover(self, dmd):
        log = logging.getLogger("zen.migrate")
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changed = False

        for service in ctx.services:
            if not service.logConfigs:
                continue

            for config in service.logConfigs:
                if config.path == "/opt/zenoss/log/audit.log" and \
                   not config.isAudit:
                    config.isAudit = True
                    changed = True

        if changed:
            ctx.commit()
        else:
            log.info('Nothing to change in this migration step.')

AddAuditLogFlag()
