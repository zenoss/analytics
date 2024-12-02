##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import Migrate

import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.1.11")

_DEFAULT_INSTANCES = 2


class IncreaseZauthDefaultInstanceCount(Migrate.Step):
    """Modify the Zauth service definition to change default instance
    count to 2 and bump the number of instances to 2 if it is currently
    less than 2.
    """

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zauth = next((s for s in ctx.services if s.name == "Zauth"), None)
        if zauth is None:
            log.info("Zauth service not found, skipping.")
            return

        changes = 0

        if zauth.instances < _DEFAULT_INSTANCES:
            zauth.instances = _DEFAULT_INSTANCES
            changes += 1
            log.info("Zauth instance count changed to %s", _DEFAULT_INSTANCES)
        else:
            log.info(
                "Zauth instance count is sufficient (%s); "
                "left unchanged", zauth.instances
            )

        if zauth.instanceLimits.default < _DEFAULT_INSTANCES:
            zauth.instanceLimits.default = _DEFAULT_INSTANCES
            changes += 1
            log.info(
                "Zauth default instance count changed to %s",
                _DEFAULT_INSTANCES
            )
        else:
            log.info(
                "Zauth default instance count is sufficient (%s); "
                "left unchanged", zauth.instanceLimits.default
            )

        if changes:
            ctx.commit()


IncreaseZauthDefaultInstanceCount()
