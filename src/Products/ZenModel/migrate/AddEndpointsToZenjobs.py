##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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


class AddEndpointsToZenjobs(Migrate.Step):
    "Add zep + zproxy endpoints to zenjobs services"

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
            ),
            'zproxy': Endpoint(
                name="zproxy",
                purpose="import",
                application="zproxy",
                portnumber=8080,
                protocol="tcp"
            )
        }

        # Get all zenjobs services (normally only 1)
        log.info("Looking for zenjobs services to migrate")
        services = filter(lambda s: s.name == "zenjobs", ctx.services)
        log.info("Found %i services named 'zenjobs'." % len(services))

        # Add the zep endpoint import if it does not exist
        if not services:
            log.info("Found no 'zenjobs' services to migrate")
            # short circuit
            return
        for service, endpoint_key in itertools.product(services, endpoint_map.keys()):
            if not filter(lambda endpoint: endpoint.purpose == "import" and endpoint.application == endpoint_key, service.endpoints):
                log.info("Adding '%s' endpoint import to service '%s'", endpoint_key, service.name)
                service.endpoints.append(
                    endpoint_map[endpoint_key]
                )

        ctx.commit()

AddEndpointsToZenjobs()
