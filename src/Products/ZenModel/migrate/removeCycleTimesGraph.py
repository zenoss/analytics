##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2011, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Remove cycleTime datapoint and graphs from collectors since they are no longer tracked.
'''

import Migrate

class RemoveCycleTimeGraph(Migrate.Step):
    version = Migrate.Version(4, 1, 70)

    def cutover(self, dmd):

        template=dmd.Monitors.rrdTemplates.PerformanceConf
        #remove selected graph points from definition if present
        graph = template.graphDefs._getOb('Cycle Times', None)
        if graph:
            graphPoints = ('zenperfsnmp', 'zenping', 'zenstatus')
            graph.manage_deleteGraphPoints(graphPoints)

        #remove threhsolds if present
        thresholdIds = ('zenperfsnmp cycle time', 'zenping cycle time', 'zenprocess cycle time')
        template.manage_deleteRRDThresholds(thresholdIds)

        #remove cycle_time datapoints from all datasources except zenmodeler
        for ds in template.datasources():
            if ds.id != 'zenmodeler' and ds.datapoints._getOb('cycleTime', False):
                ds.manage_deleteRRDDataPoints(['cycleTime'])


RemoveCycleTimeGraph()
