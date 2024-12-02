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

class SetMariaDbConfigDefaults(Migrate.Step):
    """Setting MariaDB buffer pool size default"""

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        marialist = ['mariadb', 'mariadb-model']
        marias = filter(lambda s: s.name in marialist, ctx.services)

        commit = False
        for maria in marias:

            # RAM Commitment
            if maria.ramCommitment == "2G" and maria.name == "mariadb-model":
                maria.ramCommitment = "4G"
                commit = True

            # Buffer Pool Instances
            chk  = "innodb_buffer_pool_instances = {{.CPUCommitment}}"
            repl = "innodb_buffer_pool_instances = 3"
            for cnf in maria.originalConfigs:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == chk:
                        lines[i] = repl
                cnf.content = '\n'.join(lines)
                commit = True

            for cnf in maria.configFiles:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == chk:
                        lines[i] = repl
                cnf.content = '\n'.join(lines)
                commit = True


            # Buffer Pool Size
            chk  = 'innodb_buffer_pool_size = 512M'
            repl = 'innodb_buffer_pool_size = {{percentScale .RAMCommitment 0.8}}'
            for cnf in maria.originalConfigs:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == chk:
                        lines[i] = repl
                cnf.content = '\n'.join(lines)
                commit = True

            for cnf in maria.configFiles:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == chk:
                        lines[i] = repl
                cnf.content = '\n'.join(lines)
                commit = True

        if commit:
            ctx.commit()

SetMariaDbConfigDefaults()
