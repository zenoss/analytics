##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
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

class noRabbitMQAddressAssignment(Migrate.Step):
    "Remove address assignment for RabbitMQ."

    version = Migrate.Version(109,0,0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate context, skipping.")
            return

        # Get all rabbitmq services.
        rabbits = filter(lambda s: s.name == "RabbitMQ", ctx.services)
        log.info("Found %i services named 'RabbitMQ'." % len(rabbits))

        # Unset the address assignment fields
        for rabbit in rabbits:
            endpoints = filter(lambda e: e.application == "rabbitmq", rabbit.endpoints)
            log.info("Found %i endpoints for 'rabbitmq'." % len(endpoints))
            for endpoint in endpoints:
                endpoint.addressConfig.port = 0
                endpoint.addressConfig.protocol = ""

        # Commit our changes
        ctx.commit()

noRabbitMQAddressAssignment()