##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import os
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")

class UpdateRabbitMQLogPaths(Migrate.Step):
    """
    Fix the rabbit log file location so Kibana picks them up.
    """
    version = Migrate.Version(117, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        svcs = filter(lambda s: "RabbitMQ" in s.name, ctx.services)
        log.info("Found {0} services with 'RabbitMQ' in their service path".format(len(svcs)))
        changed = False
        for svc in svcs:
            for logConfig in svc.logConfigs:
                if logConfig.logType == "rabbitmq" and "localhost" in logConfig.path:
                    log.info("Updating rabbitmq log file location")
                    logConfig.path = "/var/log/rabbitmq/rabbit@rbt[0-9]*.log"
                    changed = True
                if logConfig.logType == "rabbitmq_sasl" and "localhost" in logConfig.path:
                    log.info("Updating rabbitmq_sasl log file location")
                    logConfig.path = "/var/log/rabbitmq/rabbit@rbt[0-9]*-sasl.log"
                    changed = True
        if changed:
            # Commit our changes.
            ctx.commit()

UpdateRabbitMQLogPaths()
