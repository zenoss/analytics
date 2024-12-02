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

sm.require("1.0.0")

class SetMariaDbTimeouts51x(Migrate.Step):
    """
    Setting MariaDB timeout defaults.

    This does the same as setMariaDbTimeouts.py, but
    the version on this one is higher to account for
    upgrading systems newer than 5.0.
    """

    version = Migrate.Version(111, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        marialist = ['mariadb', 'mariadb-events', 'mariadb-model']
        marias = filter(lambda s: s.name in marialist, ctx.services)
        log.info("Found %i mariadb* services." % len(marias))

        commit = False
        for maria in marias:
            for cnf in maria.configFiles:
                if cnf.name != '/etc/my.cnf':
                    continue
                lines = cnf.content.split('\n')
                for i in range(len(lines)):
                    if lines[i] == 'wait_timeout = 86400':
                        log.info("Set wait_timeout to 7200 for in %s %s" %
                                 (maria.name, cnf.name))
                        lines[i] = 'wait_timeout = 7200'
                cnf.content = '\n'.join(lines)
                commit = True

        if commit:
            ctx.commit()

SetMariaDbTimeouts51x()
