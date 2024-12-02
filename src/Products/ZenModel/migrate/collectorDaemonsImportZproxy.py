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


class CollectorDaemonsImportZproxy(Migrate.Step):
    "Import zproxy in all collector daemons."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all services tagged "collector" and "daemon".
        collectorDaemons = filter(lambda s: all(x in s.tags for x in ["collector", "daemon"]), ctx.services)
        log.info("Found %i services tagged 'collector' or 'daemon'." % len(collectorDaemons))

        # Create the endpoint we're importing.
        endpoint = sm.Endpoint(
            name = "zproxy",
            purpose = "import",
            application = "zproxy",
            portnumber = 8080,
            protocol = "tcp",
            addressConfig = sm.AddressConfig(0, "")
        )

        # Add the endpoint to each daemon.
        for daemon in collectorDaemons:

            # Make sure we're not already importing zproxy.
            zpImports = filter(lambda ep: ep.name == "zproxy" and ep.purpose == "import", daemon.endpoints)
            if len(zpImports) > 0:
                log.info("Service %s already has a zproxy import endpoint." % daemon.name)
                continue

            log.info("Adding a zproxy import endpoint to service '%s'." % daemon.name)
            daemon.endpoints.append(endpoint)

        # Commit our changes.
        ctx.commit()

CollectorDaemonsImportZproxy()
