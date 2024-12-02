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
log.setLevel(logging.INFO)

import Migrate
import servicemigration as sm

sm.require("1.0.0")


class RunRabbitMQViaSupervisord(Migrate.Step):
    """Modify rabbitmq service to run via supervisord. """

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        log.info("Starting rabbitmq supervisord migration.")

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        content = "[supervisord]\nnodaemon=true\nlogfile = /opt/zenoss/log/supervisord.log\n\n[unix_http_server]\nfile=/tmp/supervisor.sock\n\n[supervisorctl]\nserverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket\n\n[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n\n[program:rabbitmq]\ncommand=/usr/sbin/rabbitmq-server\nautorestart=true\nautostart=true\nstartsecs=5\npriority=1\n\n[program:rabbitmq_metrics]\ncommand=/usr/bin/python /opt/zenoss/bin/metrics/rabbitstats.py\nautorestart=true\nautostart=true\nstartsecs=5\n\n; logging\nredirect_stderr=true\nstdout_logfile_maxbytes=10MB\nstdout_logfile_backups=10\nstdout_logfile=/opt/zenoss/log/%(program_name)s.log\n"
        newConfig = sm.ConfigFile(
            name="/etc/rabbitmq/rabbit_supervisor.conf",
            filename="/etc/rabbitmq/rabbit_supervisor.conf",
            owner="root:root",
            permissions="0664",
            content=content
        )

        rabbit_services = filter(lambda s: s.name == 'RabbitMQ', ctx.services)
        log.info("Found %i services named 'RabbitMQ'." % len(rabbit_services))
        changed = False
        for rabbit in rabbit_services:
            log.info("Updating rabbitmq startup command to use supervisord.")
            rabbit.startup = '/bin/supervisord -n -c /etc/rabbitmq/rabbit_supervisor.conf'

            if all([not originalConfig.name == newConfig.name for originalConfig in rabbit.originalConfigs]):
                rabbit.originalConfigs.append(newConfig)
                changed = True
                log.info("Added supervisord original config file.")

            if all([not config.name == newConfig.name for config in rabbit.configFiles]):
                rabbit.configFiles.append(newConfig)
                changed = True
                log.info("Added supervisord config file.")

        # Commit our changes.
        if changed:
            ctx.commit()
            log.info("committed changes for rabbitmq supervisord config.")


RunRabbitMQViaSupervisord()
