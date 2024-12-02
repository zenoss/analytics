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

from itertools import chain


log = logging.getLogger("zen.migrate")
sm.require("1.1.14")


class UseRabbitmqScriptLauncher(Migrate.Step):
    """Modify rabbit_supervisor.conf to use new launcher script."""

    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service = next(
            (s for s in ctx.services if s.name == "RabbitMQ"), None,
        )
        if service is None:
            log.error("Unable to find 'RabbitMQ' service")
            return

        config_files = chain(service.configFiles, service.originalConfigs)
        config_name = "/etc/rabbitmq/rabbit_supervisor.conf"
        supervisor_configs = [
            cf for cf in config_files if cf.name == config_name
        ]
        pattern = "command=/usr/sbin/rabbitmq-server"
        replacement = "command=/opt/zenoss/bin/rabbitmq.sh"
        for config in supervisor_configs:
            config.content = config.content.replace(pattern, replacement)

        if len(supervisor_configs):
            ctx.commit()
            log.info("Updated '%s' config file", config_name)
        else:
            log.error("Unable to find config file '%s'", config_name)


UseRabbitmqScriptLauncher()
