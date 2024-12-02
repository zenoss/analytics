##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add data points for configTime to zeneventlog and zenwin's data sources and the
Config Time graph.

'''
import Migrate
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint


class AddConfigTimeDataPoints(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        # get the PerformanceConf template
        template = dmd.Monitors.rrdTemplates._getOb('PerformanceConf', None)
        if not template:
            # No collector performance template exists.
            return

        # add configTime to the zeneventlog and zenwin data sources
        dpNames = []
        for ds in template.datasources():
            if ds.id not in ('zeneventlog', 'zenwin'):
                continue

            # don't try and add configTime if it already exists
            if 'configTime' in ds.datapoints.objectIds():
                continue

            newDp = ds.manage_addRRDDataPoint('configTime')
            newDp.rrdtype = 'GAUGE'
            newDp.rrdmin = 0

            dpNames.append("%s_configTime" % ds.id)

        # add the new datapoints to the config time graph
        graph = template.graphDefs._getOb("Config Time")
        if not graph:
            # No Graph Definition in the template
            return

        graph.manage_addDataPointGraphPoints(dpNames)

        # Fix up all of the graph points we just added.
        for gp in graph.graphPoints():
            if isinstance(gp, DataPointGraphPoint):
                collectorName = gp.dpName.split('_', 1)[0]
                gp.legend = collectorName

AddConfigTimeDataPoints()
