##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import itertools
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration.endpoint import Endpoint

sm.require("1.0.0")


class AddZepEndpointToZeneventd(Migrate.Step):
    "Add zep endpoint to zeneventd services"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        endpoint_map = {
            'zep': Endpoint(
                name="zep",
                purpose="import",
                application="zep",
                portnumber=8084,
                protocol="tcp"
            )
        }

        # Get all zeneventd services (normally only 1)
        log.info("Looking for zeneventd services to migrate")
        services = filter(lambda s: s.name == "zeneventd", ctx.services)
        log.info("Found %s services named 'zeneventd'.", len(services))

        # Add the zep endpoint import if it does not exist
        if not services:
            log.info("Found no 'zeneventd' services to migrate")
            # short circuit
            return
        for service, endpoint_key in itertools.product(services, endpoint_map.keys()):
            if not filter(lambda endpoint: endpoint.purpose == "import" and endpoint.application == endpoint_key, service.endpoints):
                log.info("Adding '%s' endpoint import to service '%s'", endpoint_key, service.name)
                service.endpoints.append(
                    endpoint_map[endpoint_key]
                )

        ctx.commit()

AddZepEndpointToZeneventd()

