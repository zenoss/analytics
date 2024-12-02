##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add lastSent to alert_state.

'''
import Migrate

class AnnoyingAlerts(Migrate.Step):
    version = Migrate.Version(2, 1, 0)

    def cutover(self, dmd):
        conn = dmd.ZenEventManager.connect()
        c = conn.cursor()
        c.execute('describe alert_state')
        if 'lastSent' not in [x[0] for x in c.fetchall()]:
            c.execute('alter table alert_state '
                      'add column (lastSent timestamp)')
            
AnnoyingAlerts()
