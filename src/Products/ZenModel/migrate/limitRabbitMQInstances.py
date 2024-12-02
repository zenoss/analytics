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
sm.require("1.1.9")



class LimitRabbitMQInstances(Migrate.Step):
    """
    Limit number of RabbitMQ's instances to 1.
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changed = False
        mq = [service for service in ctx.services
              if service.name == "RabbitMQ"]

        for service in mq:
            limits = service.instanceLimits
            limits.default = 1
            limits.minimum = 1
            limits.maximum = 1
            changed = True

        if changed:
            ctx.commit()
            log.info("Limit for RabbitMQ's instances was set to 1.")

LimitRabbitMQInstances()
