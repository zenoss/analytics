##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration import HealthCheck
sm.require("1.1.11")


class AddOpentsdbHbaseConnectionHealthCheck (Migrate.Step):
    """add new healthchecks to Opentsdb reader and writer for hbase connectivity
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        commit = False
        # find the target services
        tsdb_services = filter(
            lambda sc: sc.name == 'reader' or sc.name == 'writer',
            ctx.services
        )
        if len(tsdb_services) == 0:
            log.info('reader & writer service not found, look for opentsdb')
            tsdb_services = filter(
                lambda sc: sc.name == 'opentsdb',
                ctx.services
            )

        log.info('found %s services to modify', len(tsdb_services))

        # add new health checks to the services
        for svc in tsdb_services:
            health_check = HealthCheck(
                name="hbase_answering",
                interval=10.0,
                timeout=0,
                script=("curl -A 'HMaster rest_answering healthcheck'"
                        " -o /dev/null -f"
                        " -s http://localhost:61000/status/cluster")
            )

            svc.healthChecks.append(health_check)
            log.info("added 'HBase answering' healthcheck for %s.", svc.name)
            commit = True

        if commit:
            ctx.commit()


AddOpentsdbHbaseConnectionHealthCheck()
