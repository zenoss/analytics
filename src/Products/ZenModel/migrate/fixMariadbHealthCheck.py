##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class FixMariadbHealthCheck(Migrate.Step):
    """
    Use different curl request to prevent `authentication failed` spam in audit.log
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        mariadb_model = filter(lambda s: s.name == "mariadb-model", ctx.services)
        mariadb_events = filter(lambda s: s.name == "mariadb-events", ctx.services)
        mariadb_core = filter(lambda s: s.name == "mariadb", ctx.services)


        for service in mariadb_model:
            healthChecks = filter(lambda hc: hc.name == "answering", service.healthChecks)
            for check in healthChecks:
                if "mysql --protocol TCP -uroot -hlocalhost -P3306 -e 'select 1' > /dev/null" in check.script:
                    check.script = "mysql --protocol TCP -u{{(getContext . \"global.conf.zodb-admin-user\")}} -h{{(getContext . \"global.conf.zodb-host\")}} -P{{(getContext . \"global.conf.zodb-port\")}} -p{{getContext . \"global.conf.zodb-admin-password\"}} -e 'select 1' > /dev/null"
                    log.info("Updated 'answering' healthcheck for mariadb-model")

        for service in mariadb_events:
            healthChecks = filter(lambda hc: hc.name == "answering", service.healthChecks)
            for check in healthChecks:
                if "mysql --protocol TCP -uroot -hlocalhost -P3306 -e 'select 1' > /dev/null" in check.script:
                    check.script = "mysql --protocol TCP -u{{(getContext . \"global.conf.zep-admin-user\")}} -h{{(getContext . \"global.conf.zep-host\")}} -P{{(getContext . \"global.conf.zep-port\")}} -p{{getContext . \"global.conf.zep-admin-password\"}} -e 'select 1' > /dev/null"
                    log.info("Updated 'answering' healthcheck for mariadb-events")

        for service in mariadb_core:
            healthChecks = filter(lambda hc: hc.name == "answering", service.healthChecks)
            for check in healthChecks:
                if "mysql --protocol TCP -uroot -hlocalhost -P3306 -e 'select 1' > /dev/null" in check.script:
                    check.script = "mysql --protocol TCP -u{{(getContext . \"global.conf.zep-admin-user\")}} -h{{(getContext . \"global.conf.zep-host\")}} -P{{(getContext . \"global.conf.zep-port\")}} -p{{getContext . \"global.conf.zep-admin-password\"}} -e 'select 1' > /dev/null"
                    log.info("Updated 'answering' healthcheck for mariadb")

        ctx.commit()
FixMariadbHealthCheck()
