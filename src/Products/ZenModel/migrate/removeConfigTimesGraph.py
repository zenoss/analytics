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

class RemoveConfigTimesGraph(Migrate.Step):
    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):

        template = dmd.Monitors.rrdTemplates.PerformanceConf
        graph = template.graphDefs._getOb('Config Time', None)

        if graph is not None:
            template.graphDefs.removeRelation(graph)

        #remove configTime datapoints from all datasources
        for ds in template.datasources():
            if ds.datapoints._getOb('configTime', False):
                ds.manage_deleteRRDDataPoints(['configTime'])


RemoveConfigTimesGraph()
