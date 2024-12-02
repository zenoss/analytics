##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add usercommands to all device organizers, OsProcesses, Services, etc

$Id:$
'''
import Migrate
from Products.ZenEvents.EventClass import manage_addEventClass

class addWinService(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if 'Status' not in [c.id for c in dmd.Events.children()]:
            manage_addEventClass(dmd.Events, 'Status')
        if 'WinService' not in [c.id for c in dmd.Events.Status.children()]:
            manage_addEventClass(dmd.Events.Status, 'WinService')


addWinService()
