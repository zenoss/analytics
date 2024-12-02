##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Increase eventKey length from 64 to 128 characters.

'''
import Migrate

import logging
log = logging.getLogger("zen.migrate")

class ExpandEventKeyColumn(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        conn = dmd.ZenEventManager.connect()
        c = conn.cursor()
        for table in ('history', 'status'):
            c.execute('describe %s' % (table,))
            for col in c.fetchall():
                if col[0] == 'eventKey' and col[1] == 'varchar(64)':
                    c.execute('alter table %s modify eventKey varchar(128)' %
                            (table,))


ExpandEventKeyColumn()
