##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm

log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class UpdateZeneventserverMariaDBHealthCheck(Migrate.Step):
    version = Migrate.Version(200, 5, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zeps = filter(lambda s: s.name == "zeneventserver", ctx.services)
        log.info("Found %i services named 'zeneventserver'." % len(zeps))

        updated = False
        for zep in zeps:
            mdb_answerings = filter(lambda hc: hc.name == "mariadb_answering", zep.healthChecks)
            log.info("Found %i 'mariadb_answering' healthchecks." % len(mdb_answerings))
            for answering in mdb_answerings:
                answering.name = "mariadb_events_answering"
                answering.script = "su - zenoss -c '/opt/zenoss/bin/python /opt/zenoss/Products/ZenUtils/ZenDB.py --usedb zep --execsql=\";\"'"
                updated = True
                log.info("Updated 'mariadb_answering' healthcheck.")

        if updated:
            ctx.commit()


UpdateZeneventserverMariaDBHealthCheck()

