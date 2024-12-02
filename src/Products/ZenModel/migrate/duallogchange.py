##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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


class DualLogChange(Migrate.Step):
    "Change services to use logfileonly option"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Alter their startup command and instanceLimits.
        for svc in ctx.services:
            if svc.startup and svc.startup.find('--duallog') >= 0:
                svc.startup = svc.startup.replace('--duallog', '--logfileonly')
                log.info("Changed startup command for service '%s'." % svc.name)

        # Commit our changes.
        ctx.commit()


DualLogChange()
