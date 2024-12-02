##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

class RemoveWinModelerGraphPoints(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def deleteLastObjectOnPath(self, dmd, path):
        parts = path.split('/')
        obj = dmd
        for part in parts[:-1]:
            obj = obj._getOb(part)
        obj._delObject(parts[-1])

    def cutover(self, dmd):
        base = 'Monitors/rrdTemplates/PerformanceConf/'
        paths = [
            base + 'graphDefs/Cycle Times/graphPoints/zenwinmodeler',
            base + 'thresholds/zenwinmodeler cycle time',
            base + 'datasources/zenwinmodeler',
            ]
        for path in paths:
            try:
                self.deleteLastObjectOnPath(dmd, path)
            except AttributeError:
                pass
            

RemoveWinModelerGraphPoints()
