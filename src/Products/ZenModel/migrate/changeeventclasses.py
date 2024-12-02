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

class ChangeEventClasses(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if 'Change' not in [c.id for c in dmd.Events.children()]:
            manage_addEventClass(dmd.Events, 'Change')
        dmd.Events.Change.zEventAction = 'history'
        for name in ['Add', 'Remove', 'Set']:
            if name not in [c.id for c in dmd.Events.Change.children()]:
                manage_addEventClass(dmd.Events.Change, name)


ChangeEventClasses()
