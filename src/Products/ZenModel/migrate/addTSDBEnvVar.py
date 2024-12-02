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

sm.require("1.1.10")


class AddTSDBEnvVar(Migrate.Step):
    "Add RAMCommitment to environment as -xmx flag for opentsdb services."

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        env_entry = "TSDB_JAVA_MEM_MB=-Xmx{{bytesToMB .RAMCommitment}}m"

        tsdb_services = [s for s in ctx.services if 'start-opentsdb.sh' in s.startup]
        changed = False
        for tsdb_svc in tsdb_services:
            if env_entry not in tsdb_svc.environment:
                tsdb_svc.environment.append(env_entry)
                changed = True

        if changed:
            ctx.commit()

AddTSDBEnvVar()
