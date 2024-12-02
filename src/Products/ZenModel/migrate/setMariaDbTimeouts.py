##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
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

class SetMariaDbTimeouts(Migrate.Step):
    """Setting MariaDB timeout defaults"""

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        marialist = ['mariadb', 'mariadb-events', 'mariadb-model']
        marias = filter(lambda s: s.name in marialist, ctx.services)

        commit = False
        for maria in marias:
            for cnf in maria.configFiles:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == 'wait_timeout = 86400':
                        lines[i] = 'wait_timeout = 7200'
                cnf.content = '\n'.join(lines)
                commit = True
                
        if commit:
            ctx.commit()

SetMariaDbTimeouts()
