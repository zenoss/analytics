##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import servicemigration as sm
import Migrate

log = logging.getLogger("zen.migrate")
sm.require("1.1.13")


class MarkHubServices(Migrate.Step):
    """Update hub services' tags with "hub" marker."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        total = 0
        zenhubs = (s for s in ctx.services if s.name == "zenhub")
        for zenhub in zenhubs:
            hub = ctx.getServiceParent(zenhub)
            services_not_tagged_with_hub = (
                s for s in ctx.getServiceChildren(hub)
                if "daemon" in s.tags and "hub" not in s.tags
            )
            count = 0
            for service in services_not_tagged_with_hub:
                service.tags.append("hub")
                count += 1
            log.info("Hub '%s': marked %s services", hub.name, count)
            total += count

        if total > 0:
            ctx.commit()


MarkHubServices()
