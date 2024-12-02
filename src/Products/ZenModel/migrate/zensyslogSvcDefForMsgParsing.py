###############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

__doc__ = """
Update zensyslog graphs config to add eventParserDroppedCount number.
"""

import logging

import Migrate
import servicemigration as sm

from servicemigration.metrics import Metric
from servicemigration.graphdatapoint import GraphDatapoint



log = logging.getLogger("zen.migrate")
svcNamesToUpdate = ['zensyslog']
sm.require("1.0.0")


class ZensyslogSvcDevForMsgParsing(Migrate.Step):
    '''
    add 'Parser Dropped Events' to zensyslog 'Events' graph
    '''

    version = Migrate.Version(200, 7, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.error("Couldn't generate service context, skipping.")
            return

        commit = False

        svcs = filter(lambda s: s.name in svcNamesToUpdate, ctx.services)
        log.info("Found %i %r services to update.", len(svcs), svcNamesToUpdate)
        for svc in svcs:
            collectorName = ctx.getServiceParent(svc).name
            # Update the existing 'Events' graph with new graphpoint
            gc = next(
                (x for x in svc.monitoringProfile.graphConfigs if x.name == 'Events'),
                None
            )
            if gc is None:
                log.error(
                    "%s %s service: No 'Events' graph configuration found; "
                    "broken service def; skipping.", collectorName, svc.name)
                continue
            if not filter(lambda x: x.pointID == "eventParserDroppedCount", gc.datapoints):
                log.info(
                    "%s %s service: Adding 'Parser Dropped Events' graphpoint to the"
                    " 'Events' graph.", collectorName, svc.name)
                gc.datapoints.append(
                    GraphDatapoint(
                            aggregator='avg',
                            fill=False,
                            pointID='eventParserDroppedCount',
                            legend='eventParserDroppedCount',
                            metric='eventParserDroppedCount',
                            metricSource='zensyslog',
                            name='Parser Dropped Events',
                            rate=False,
                            pointType='line'
                    )
                )
                commit = True
            else:
                log.info(
                    "%s %s service: 'Parser Dropped Events' graphpoint exists"
                    " on the 'Events' graph; skipping.", collectorName, svc.name)
            # Add new Service metric
            mc = next(
                (x for x in svc.monitoringProfile.metricConfigs
                    if x.name == 'zensyslog internal metrics'),
                None
            )
            if mc is None:
                log.error(
                    "%s %s service: No 'zensyslog internal metrics' metric "
                    "config found; broken service def; skipping.", collectorName, svc.name)
                continue
            else:
                if not filter(lambda x: x.ID == "eventParserDroppedCount", mc.metrics):
                    log.info(
                        "%s %s service: Adding 'Parser Dropped Events' "
                        "metric", collectorName, svc.name)
                    mc.metrics.append(
                        Metric(
                            ID='eventParserDroppedCount',
                            name='Parser Dropped Events',
                            unit='Events',
                            description='Total number of Parser-Dropped events.',
                            counter=False
                        )
                    )
                    commit = True
                else:
                    log.info(
                        "%s %s service: 'Parser Dropped Events' metric "
                        "exists; skipping.", collectorName, svc.name)

        if commit:
            ctx.commit()


ZensyslogSvcDevForMsgParsing()
