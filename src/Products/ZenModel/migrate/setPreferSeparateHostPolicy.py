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

_SELECT_SERVICES = ("zenhub", "Zope", "zeneventd")


class SetPreferSeparateHostPolicy(Migrate.Step):
    """Set HostPolicy to PREFER_SEPARATE for select Control Center services.
    """

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Locate the services to modify.
        services = [s for s in ctx.services if s.name in _SELECT_SERVICES]
        migrated = 0
        for service in services:

            if service.name == "zenhub":
                monitor = ctx.getServiceParent(service)
                svcName = "%s/%s" % (monitor.name, service.name)
            else:
                svcName = service.name

            # Skip services that already have their HostPolicy set.
            if service.hostPolicy:
                log.info(
                    "Skipping service %s; HostPolicy already set to '%s'",
                    svcName, service.hostPolicy
                )
                continue

            service.hostPolicy = "PREFER_SEPARATE"
            log.info(
                "Set service %s's HostPolicy to 'PREFER_SEPARATE'", svcName
            )
            migrated += 1

        ctx.commit()
        log.info(
            "Migrated %s service%s", migrated, "s" if migrated != 1 else ""
        )


SetPreferSeparateHostPolicy()
