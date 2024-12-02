##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''

Add data points, a threshold and a graph for tracking each daemon's event queue
length.

'''
import Migrate
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint


class AddEventQueueLength(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def cutover(self, dmd):
        template = dmd.Monitors.rrdTemplates._getOb('PerformanceConf', None)
        if not template:
            # No collector performance template exists.
            return

        # Add eventQueueLength data point to each data source in the template.
        dsnames = []
        for ds in template.datasources():
            dsnames.append(ds.id)

            if 'eventQueueLength' in ds.datapoints.objectIds():
                continue

            newDp = ds.manage_addRRDDataPoint('eventQueueLength')
            newDp.rrdtype = 'GAUGE'
            newDp.rrdmin = 0

        dpnames = [ '%s_eventQueueLength' % dsname for dsname in dsnames ]

        # Create a threshold for >1000 events in queue.
        if 'high event queue' not in template.thresholds.objectIds():
            threshold = template.manage_addRRDThreshold(
                'high event queue', 'MinMaxThreshold')

            threshold.maxval = '1000'
            threshold.eventClass = '/Perf'
            threshold.severity = 4
            threshold.dsnames = dpnames

        # Add an Event Queue graph.
        if 'Event Queue' not in template.graphDefs.objectIds():
            graph = template.manage_addGraphDefinition('Event Queue')
            graph.units = 'events'
            graph.miny = 0

            graph.manage_addDataPointGraphPoints(
                dpnames, includeThresholds=True)

            # Fix up all of the graph points we just added.
            for gp in graph.graphPoints():
                if isinstance(gp, DataPointGraphPoint):
                    gp.stacked = True
                    gp.lineType = DataPointGraphPoint.LINETYPE_AREA
                    gp.format = '%6.0lf'
                    gp.legend = gp.dpName.split('_', 1)[0]

            # Put the Event Queue graph right after Cycle Times
            inserted = False
            for g in template.getGraphDefs():
                if g.id == 'Cycle Times':
                    graph.sequence = g.sequence + 1
                    inserted = True
                elif g.id != 'Event Queue' and inserted:
                    g.sequence = g.sequence + 1


AddEventQueueLength()
