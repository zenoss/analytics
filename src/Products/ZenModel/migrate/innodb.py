##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='Convert MEMORY tables to INNODB'

import logging
log = logging.getLogger("zen.migrate")

import Migrate

class Innodb(Migrate.Step):
    version = Migrate.Version(1, 0, 0)

    def cutover(self, unused):
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            curs.execute('SHOW TABLE STATUS')
            for row in curs.fetchall():
                table, engine = row[:2]
                options = row[-2]
                if engine == 'MEMORY':
                    log.debug('Converting table %s' % table)
                    curs.execute('ALTER TABLE %s ENGINE=INNODB' % table)
                if options and options.find('max_rows=') >= 0:
                    curs.execute('ALTER TABLE %s max_rows=0' % table)
        finally: zem.close(conn)

Innodb()
