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

class EventNewClasses(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        dmd.Events.createOrganizer("/Perf/XmlRpc")
        dmd.Events.createOrganizer("/Status/Perf")
        dmd.Events.createOrganizer("/Status/Update")
        dmd.ZenEventManager.buildRelations()

EventNewClasses()
