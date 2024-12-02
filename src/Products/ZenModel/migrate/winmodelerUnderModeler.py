##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class WinModelerUnderModeler(Migrate.Step):

    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        import os
        from Products.ZenUtils.Utils import binPath
        os.system('%s stop >/dev/null 2>&1' % binPath('zenwinmodeler'))
        conn = dmd.ZenEventManager.connect()
        curr = conn.cursor()
        curr.execute("delete from heartbeat where component = 'zenwinmodeler'")

WinModelerUnderModeler()
