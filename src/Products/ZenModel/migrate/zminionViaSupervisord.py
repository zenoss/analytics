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


class RunZminionViaSupervisord(Migrate.Step):
    """Modify zminion to run via supervisord and forward logs to logstash. """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zminion_services = filter(lambda s: s.name == 'zminion', ctx.services)
        log.info("Found %i services named 'zminion'." % len(zminion_services))
        for zminion in zminion_services:
            zminion.logConfigs = zminion.logConfigs or []
            logfiles = [z.path for z in zminion.logConfigs]
            log_path = "/opt/zenoss/log/zminion.log"
            if log_path not in logfiles:
                log.info("Updating zminion startup command to use supervisord.")
                zminion.startup = 'su - zenoss -c "/bin/supervisord -n -c /opt/zenoss/etc/zminion/supervisord.conf"'
                log.info("Adding supervisord to logConfigs.")
                zminion.logConfigs.append(sm.LogConfig(path=log_path, logType="zminion"))
            else:
                log.info("Service 'zminion' already has an /opt/zenoss/log/zminion.log; skipping.")

        # Commit our changes.
        ctx.commit()


RunZminionViaSupervisord()
