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
sm.require("1.1.5")

from serviceRunLevels import serviceRunLevels


class AddServiceRunLevels(Migrate.Step):
    """
    Add the emergency shutdown and startup levels to service definitions.
    See ZEN-23931, ZEN-27299.
    """

    version = Migrate.Version(109, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changed = False

        for service in ctx.services:
            emergencyShutdownLevel, startLevel = serviceRunLevels.get(service.name, (0, 0))
            if not service.emergencyShutdownLevel == emergencyShutdownLevel:
                before = service.emergencyShutdownLevel
                service.emergencyShutdownLevel = emergencyShutdownLevel
                changed = True
                log.info('Change emergency shutdown level of %s from %d to %d.', service.name, before, emergencyShutdownLevel)
            if not service.startLevel == startLevel:
                before = service.startLevel
                service.startLevel = startLevel
                changed = True
                log.info('Change start level of %s from %d to %d.', service.name, before, startLevel)

        if changed:
            ctx.commit()
        else:
            log.info('Nothing to change in this migration step.')

AddServiceRunLevels()
