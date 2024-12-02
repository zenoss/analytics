##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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

class UpdateMariaDBPoolAlloc(Migrate.Step):
    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        mariaservices = filter(lambda s: "mariadb" in s.name, ctx.services)
        log.info("Found {0} services with 'mariadb' in their service path".format(len(mariaservices)))
        for m in mariaservices:
            log.info("{0}".format(m))
            cfs = filter(lambda f: f.name == "/etc/my.cnf", m.originalConfigs + m.configFiles)
            for cf in cfs:
                lines = cf.content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith("innodb_buffer_pool_size") and "512M" in line:
                        lines[i] = line.replace("512M", "{{percentScale .RAMCommitment 0.8}}")
                        log.info("Changed MariaDB innodb_buffer_pool_size from 512M (default) to '{{percentScale .RAMCommitment 0.8}}' on line {0}".format(i))
                cf.content = '\n'.join(lines)
        # Commit our changes.
        ctx.commit()

UpdateMariaDBPoolAlloc()
