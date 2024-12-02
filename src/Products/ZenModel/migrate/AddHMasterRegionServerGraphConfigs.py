##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration.metrics import Metric
from servicemigration.graphrange import GraphRange
from servicemigration.graphconfig import GraphConfig
from servicemigration.metricconfig import MetricConfig
from servicemigration.graphdatapoint import GraphDatapoint
sm.require("1.0.0")


class AddHMasterRegionServerGraphConfigs(Migrate.Step):
    """ Add GraphConfigs and MetricConfigs to HMaster and RegionServer """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all HMaster and RegionServer services.
        hmServices = filter(lambda s: s.name == "HMaster", ctx.services)
        log.info("Found %i services named 'HMaster'." % len(hmServices))
        rsServices = filter(lambda s: s.name == "RegionServer", ctx.services)
        log.info("Found %i services named 'RegionServer'." % len(rsServices))

        # Add graph config to monitoring profile
        commit = False
        for hmService in hmServices:
            gcs = hmService.monitoringProfile.graphConfigs
            mcs = hmService.monitoringProfile.metricConfigs
            if not filter(lambda x: x.graphID == 'logStats', gcs):
                log.info("No logStats graph found; creating.")
                gcs.append(
                    GraphConfig(
                        graphID='logStats',
                        name='Log Stats',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        yAxisLabel='events',
                        description='Log Stats',
                        graphRange=GraphRange(
                            start='10s-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=False,
                                pointID='LogFatal',
                                legend='Total number of fatal log events',
                                metric='LogFatal',
                                metricSource='HMaster',
                                name='Total number of fatal log events',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='LogError',
                                legend='Total number of error log events',
                                metric='LogError',
                                metricSource='HMaster',
                                name='Total number of error log events',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='LogWarn',
                                legend='Total number of warn log events',
                                metric='LogWarn',
                                metricSource='HMaster',
                                name='Total number of warn log events',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("logStats graph found; skipping.")

            if not filter(lambda x: x.graphID == 'regionServers', gcs):
                log.info("No regionServers graph found; creating.")
                gcs.append(
                    GraphConfig(
                        graphID='regionServers',
                        name='Region Servers',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        yAxisLabel='servers',
                        description='Region Servers',
                        graphRange=GraphRange(
                            start='10s-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='numRegionServers',
                                legend='Total number of live regions servers',
                                metric='numRegionServers',
                                metricSource='HMaster',
                                name='Total number of live regions servers',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='numDeadRegionServers',
                                legend='Total number of dead regions servers',
                                metric='numDeadRegionServers',
                                metricSource='HMaster',
                                name='Total number of dead regions servers',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("regionServers graph found; skipping.")

            if not filter(lambda x: x.ID == 'HMaster', mcs):
                log.info("No HMaster internal metrics found; creating.")
                mcs.append(
                    MetricConfig(
                        ID='HMaster',
                        name='HMaster internal metrics',
                        description='HMaster internal metrics',
                        metrics=[
                            Metric(
                                ID='LogFatal',
                                name='Total number of fatal log events'
                            ),
                            Metric(
                                ID='LogError',
                                name='Total number of error log events'
                            ),
                            Metric(
                                ID='LogWarn',
                                name='Total number of warn log events'
                            ),
                            Metric(
                                ID='numRegionServers',
                                name='Total number of live regions servers'
                            ),
                            Metric(
                                ID='numDeadRegionServers',
                                name='Total number of dead regions servers'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("HMaster internal metrics found; skipping.")

        for rsService in rsServices:
            gcs = rsService.monitoringProfile.graphConfigs
            mcs = rsService.monitoringProfile.metricConfigs
            if not filter(lambda x: x.graphID == 'QueueLength', gcs):
                log.info("No QueueLength graph found; creating.")
                gcs.append(
                    GraphConfig(
                        graphID='QueueLength',
                        name='Queue Length',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        yAxisLabel='Blocks of items',
                        description='Queue Length',
                        graphRange=GraphRange(
                            start='10s-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=False,
                                pointID='numCallsInGeneralQueue',
                                legend='Current depth of the User Requests',
                                metric='numCallsInGeneralQueue',
                                metricSource='RegionServer',
                                name='Current depth of the User Requests',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='numCallsInPriorityQueue',
                                legend='Current depth of the Internal Housekeeping Requests queue',
                                metric='numCallsInPriorityQueue',
                                metricSource='RegionServer',
                                name='Current depth of the Internal Housekeeping Requests queue',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='flushQueueLength',
                                legend='Current depth of the memstore flush queue',
                                metric='flushQueueLength',
                                metricSource='RegionServer',
                                name='Current depth of the memstore flush queue',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='compactionQueueLength',
                                legend='Current depth of the compaction request queue',
                                metric='compactionQueueLength',
                                metricSource='RegionServer',
                                name='Current depth of the compaction request queue',
                                rate=False,
                                rateOptions={
                                    'counter': True,
                                    'counterMax': None,
                                    'resetThreshold': 1048576
                                },
                                pointType='line'
                            )

                        ]
                    )
                )
                commit = True
            else:
                log.info("QueueLength graph found; skipping.")

            if not filter(lambda x: x.graphID == 'slowOps', gcs):
                log.info("No slowOps graph found; creating.")
                gcs.append(
                    GraphConfig(
                        graphID='slowOps',
                        name='Slow Operations',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        yAxisLabel='Operations',
                        description='Slow Operations',
                        graphRange=GraphRange(
                            start='10s-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='slowAppendCount',
                                legend='The number of slow append operations',
                                metric='slowAppendCount',
                                metricSource='RegionServer',
                                name='The number of slow append operations',
                                rate=False,
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='slowDeleteCount',
                                legend='The number of slow delete operations',
                                metric='slowDeleteCount',
                                metricSource='RegionServer',
                                name='The number of slow delete operations',
                                rate=False,
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='slowGetCount',
                                legend='The number of slow get operations',
                                metric='slowGetCount',
                                metricSource='RegionServer',
                                name='The number of slow get operations',
                                rate=False,
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='slowIncrementCount',
                                legend='The number of slow increment operations',
                                metric='slowIncrementCount',
                                metricSource='RegionServer',
                                name='The number of slow increment operations',
                                rate=False,
                                pointType='line'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("slowOps graph found; skipping.")

            if not filter(lambda x: x.graphID == 'opcounts', gcs):
                log.info("No opcounts graph found; creating.")
                gcs.append(
                    GraphConfig(
                        graphID='opcounts',
                        name='Operation Counts',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        yAxisLabel='Operations',
                        description='Slow Operations',
                        graphRange=GraphRange(
                            start='10s-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='totalRequestCount',
                                legend='The total number of requests received',
                                metric='totalRequestCount',
                                metricSource='RegionServer',
                                name='The total number of requests received',
                                rate=False,
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='readRequestCount',
                                legend='The total number of read requests received',
                                metric='readRequestCount',
                                metricSource='RegionServer',
                                name='The total number of read requests received',
                                rate=False,
                                pointType='line'
                            ),
                            GraphDatapoint(
                                aggregator='zimsum',
                                fill=True,
                                pointID='writeRequestCount',
                                legend='The total number of write requests received',
                                metric='writeRequestCount',
                                metricSource='RegionServer',
                                name='The total number of write requests received',
                                rate=False,
                                pointType='line'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("opcounts graph found; skipping.")

            if not filter(lambda x: x.ID == 'RegionServer', mcs):
                log.info("No RegionServer internal metrics found; creating.")
                mcs.append(
                    MetricConfig(
                        ID='RegionServer',
                        name='RegionServer internal metrics',
                        description='RegionServer internal metrics',
                        metrics=[
                            Metric(
                                ID='numCallsInGeneralQueue',
                                name='Current depth of the User Requests'
                            ),
                            Metric(
                                ID='numCallsInPriorityQueue',
                                name='Current depth of the Internal Housekeeping Requests queue'
                            ),
                            Metric(
                                ID='flushQueueLength',
                                name='Current depth of the memstore flush queue'
                            ),
                            Metric(
                                ID='compactionQueueLength',
                                name='Current depth of the compaction request queue'
                            ),
                            Metric(
                                ID='slowAppendCount',
                                name='The number of slow append operations'
                            ),
                            Metric(
                                ID='slowDeleteCount',
                                name='The number of slow delete operations'
                            ),
                            Metric(
                                ID='slowGetCount',
                                name='The number of slow get operations'
                            ),
                            Metric(
                                ID='slowIncrementCount',
                                name='The number of slow increment operations'
                            ),
                            Metric(
                                ID='totalRequestCount',
                                name='The total number of requests received'
                            ),
                            Metric(
                                ID='readRequestCount',
                                name='The total number of read requests received'
                            ),
                            Metric(
                                ID='writeRequestCount',
                                name='The total number of write requests received'
                            )
                        ]
                    )
                )
                commit = True
            else:
                log.info("RegionServer internal metrics found; skipping.")

        # Commit our changes.
        if commit:
            ctx.commit()


AddHMasterRegionServerGraphConfigs()
