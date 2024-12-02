##############################################################################
#
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

import Migrate

from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint

_LOG = logging.getLogger('zen.migrate')

class AddMissedRunsMonitorGraph(Migrate.Step):

    version = Migrate.Version(4, 2, 70)

    def cutover(self, dmd):
        template = dmd.Monitors.rrdTemplates.PerformanceConf

        for datasource in template.datasources():
            try:
                missedRunsDataPoint = datasource.missedRuns
            except AttributeError:
                missedRunsDataPoint = datasource.manage_addRRDDataPoint('missedRuns')

            if missedRunsDataPoint.rrdtype != 'GAUGE': missedRunsDataPoint.rrdtype = 'GAUGE'


        try:
            gdName = 'Missed Runs'
            missedRunsGraphDef = template.graphsDefs._getOb(gdName)
        except AttributeError:
            missedRunsGraphDef = template.manage_addGraphDefinition(gdName)
            graphPoints = ['zencommand_missedRuns','zenperfsnmp_missedRuns','zenping_missedRuns',
             'zenprocess_missedRuns','zenstatus_missedRuns','zenwin_missedRuns']

            for dpName in graphPoints:
                dpId = dpName.split('_', 1)[0]
                gp = missedRunsGraphDef.createGraphPoint(DataPointGraphPoint, dpId)
                gp.dpName = dpName

AddMissedRunsMonitorGraph()

