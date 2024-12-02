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
from servicemigration.graphconfig import GraphConfig
from servicemigration.graphrange import GraphRange
from servicemigration.graphdatapoint import GraphDatapoint
sm.require("1.0.0")


class AddCentralQueryGraphConfigs(Migrate.Step):
    """ Add GraphConfigs to Central Query """

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all Central Query services.
        services = filter(lambda s: s.name == "CentralQuery", ctx.services)
        log.info("Found %i services named 'CentralQuery'." % len(services))

        # Add graph config to monitoring profile
        commit = False
        for service in services:
            gcs = service.monitoringProfile.graphConfigs
            if not filter(lambda x: x.graphID == "queryRate", gcs):
                log.info("No queryRate graph found; creating.")
                commit = True
                gcs.append(
                    GraphConfig(
                        graphID='queryRate',
                        name='Query Rate',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        yAxisLabel='Query Rate',
                        description='Number of queries received per second.',
                        graphRange=GraphRange(
                            start='1h-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='avg',
                                fill=False,
                                pointID='Queries',
                                legend='Queries',
                                metric='ZEN_INF.org.zenoss.app.metricservice.api.metric.remote.MetricResources.query.count',
                                metricSource='MetricResources.query',
                                name='Queries',
                                rate=True,
                                pointType='line'
                            )
                        ]
                    )
                )
            else:
                log.info("QueryRate graph found; skipping.")

        # Commit our changes.
        if commit:
            ctx.commit()

AddCentralQueryGraphConfigs()
