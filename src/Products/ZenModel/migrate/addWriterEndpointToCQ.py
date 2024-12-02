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


class AddWriterEndpointToCQ(Migrate.Step):
    "Add opentsdb-writer endpoint to CentralQuery services"

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        endpoint_map = {
            'opentsdb-writer': Endpoint(
                name="opentsdb-writer",
                purpose="import",
                application="opentsdb-writer",
                applicationtemplate="opentsdb-writer",
                portnumber=4243,
                protocol="tcp"
            )
        }

        # Get all CentralQuery services (normally only 1)
        log.info("Looking for CentralQuery services to migrate")
        services = filter(lambda s: s.name == "CentralQuery", ctx.services)
        log.info("Found %i services named 'CentralQuery'." % len(services))

        if not services:
            log.info("Found no 'CentralQuery' services to migrate")
            return

        # Add the opentsdb-writer endpoint import if it does not exist
        changed = False
        for service, endpoint_key in itertools.product(services, endpoint_map.keys()):
            if not filter(lambda endpoint: endpoint.purpose == "import" and endpoint.application == endpoint_key, service.endpoints):
                log.info("Adding '%s' endpoint import to service '%s'", endpoint_key, service.name)
                service.endpoints.append(
                    endpoint_map[endpoint_key]
                )
                changed = True

        if changed:
            ctx.commit()

AddWriterEndpointToCQ()
