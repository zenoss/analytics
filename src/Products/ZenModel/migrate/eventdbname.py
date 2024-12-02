##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''EventDBName

Add database to dmd.ZenEventManager

'''
import Migrate

class EventDBName(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.ZenEventManager, 'host'):
            dmd.ZenEventManager.host = dmd.ZenEventManager.database
            dmd.ZenEventManager.database = 'events'
        if not hasattr(dmd.ZenEventHistory, 'host'):
            dmd.ZenEventHistory.host = dmd.ZenEventHistory.database
            dmd.ZenEventHistory.database = 'events'

EventDBName()
