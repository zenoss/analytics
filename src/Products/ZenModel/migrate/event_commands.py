##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='Add commands to EventManager'

import Migrate

class EventCommands(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        dmd.Events.createOrganizer("/Status/Web")
        dmd.Events.createOrganizer("/Cmd/Ok")
        dmd.Events.createOrganizer("/Cmd/Fail")
        dmd.ZenEventManager.buildRelations()

EventCommands()
