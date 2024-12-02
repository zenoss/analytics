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
Update zentrap graphs config to add eventFilterDroppedCount number.
"""

import logging
import re

import Migrate
import servicemigration as sm

from servicemigration.metrics import Metric
from servicemigration.graphrange import GraphRange
from servicemigration.graphconfig import GraphConfig
from servicemigration.graphdatapoint import GraphDatapoint



log = logging.getLogger("zen.migrate")
svcNamesToUpdate = ['zentrap']
sm.require("1.0.0")


class ZentrapSvcDevForMsgParsing(Migrate.Step):
    '''
    add 'Filter Dropped Events' to zentrap 'Events' graph
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
            # Update new global config with any previous, file defined filters
            fc = next(
                (x for x in svc.configFiles if x.name == '/opt/zenoss/etc/zentrap.filter.conf'),
                None
            )
            collectorName = ctx.getServiceParent(svc).name
            if fc is None:
                log.error(
                    "%s %s service: No 'zentrap.filter.conf' File configuration found; "
                    "broken service def; skipping.", collectorName, svc.name)
                continue

            ofc = next(
                (x for x in svc.originalConfigs if x.name == '/opt/zenoss/etc/zentrap.filter.conf'),
                None
            )
            if fc.content == ofc.content:
                log.info(
                    "%s %s service: 'zentrap.filter.conf' contents are the default"
                    "; skipping.", collectorName, svc.name)
            else:
                log.info(
                    "%s %s service: found collector specific trap filter "
                    "configurations in 'zentrap.filter.conf'",
                    collectorName, svc.name)
                collectorCfg = []
                for lineNumber, line in enumerate(fc.content.split('\n')):
                    if line.startswith('#'):
                        continue
                    # skip blank lines
                    if not line.strip():
                        continue
                    if not re.search(
                            '^({} )*{}$'.format(
                                collectorName,
                                line.replace('*', '\*')),
                            dmd.ZenEventManager.trapFilters,
                            re.MULTILINE):
                        log.info(
                            '%s %s service: migrating to global config. "%s %s"',
                            collectorName, svc.name,
                            collectorName, line)
                        collectorCfg.append("{} {}".format(
                            collectorName,
                            line))
                if collectorCfg:
                    collectorCfg.insert(
                        0,
                        '# Migrated from {} "zentrap.filter.conf" file.'.format(
                            collectorName
                        )
                    )
                    collectorCfg.insert(0, '')
                    collectorCfg.append('')
                    dmd.ZenEventManager.trapFilters += '\n'.join(collectorCfg)
                else:
                    log.info(
                        '%s %s service: No configs migrated, must be already defined/migrated.',
                        collectorName, svc.name)

            # 'Events' graph ....
            gc = next(
                (x for x in svc.monitoringProfile.graphConfigs if x.name == 'Events'),
                None
            )
            if gc is None:
                # 'Events' graph is missing ?!?
                log.info(
                    "%s %s service: No 'Events' graph configuration found; "
                    "creating it.", collectorName, svc.name)
                gcs = svc.monitoringProfile.graphConfigs
                gcs.insert(
                    2,
                    GraphConfig(
                        graphID="events",
                        name="Events",
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        yAxisLabel='Events',
                        description='Events',
                        graphRange=GraphRange(
                            start='1h-ago',
                            end='0s-ago'
                        ),
                        units="Events",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="avg",
                                fill=False,
                                pointID="events",
                                legend="Queued",
                                metric="events",
                                metricSource="zentrap",
                                name="Events",
                                rate=True,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="avg",
                                fill=False,
                                pointID="events",
                                legend="Events",
                                metric="eventCount",
                                metricSource="zentrap",
                                name="Event Count",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator='avg',
                                fill=False,
                                pointID='eventFilterDroppedCount',
                                legend='eventFilterDroppedCount',
                                metric='eventFilterDroppedCount',
                                metricSource='zentrap',
                                name='Filter Dropped Events',
                                rate=False,
                                pointType='line'
                            )
                        ]
                    )
                )
            else:
                # Update the existing 'Events' graph with new graphpoint
                if not filter(lambda x: x.pointID == "eventFilterDroppedCount", gc.datapoints):
                    log.info(
                        "%s %s service: Adding 'Filter Dropped Events' graphpoint to the"
                        " 'Events' graph.", collectorName, svc.name)
                    gc.datapoints.append(
                        GraphDatapoint(
                            aggregator='avg',
                            fill=False,
                            pointID='eventFilterDroppedCount',
                            legend='eventFilterDroppedCount',
                            metric='eventFilterDroppedCount',
                            metricSource='zentrap',
                            name='Filter Dropped Events',
                            rate=False,
                            pointType='line'
                        )
                    )
                    commit = True
                else:
                    log.info(
                        "%s %s service: 'Filter Dropped Events' graphpoint exists"
                        " on the 'Events' graph; skipping.", collectorName, svc.name)
            # Add new Service metric
            mc = next(
                (x for x in svc.monitoringProfile.metricConfigs
                    if x.name == 'zentrap internal metrics'),
                None
            )
            if mc is None:
                log.error(
                    "%s %s service: No 'zentrap internal metrics' metric "
                    "config found; broken service def; skipping.", collectorName, svc.name)
                continue
            else:
                if not filter(lambda x: x.ID == "eventFilterDroppedCount", mc.metrics):
                    log.info(
                        "%s %s service: Adding 'Filter Dropped Events' "
                        "metric", collectorName, svc.name)
                    mc.metrics.append(
                        Metric(
                            ID='eventFilterDroppedCount',
                            name='Filter Dropped Events',
                            unit='Events',
                            description='Total number of Filter-Dropped events.',
                            counter=False
                        )
                    )
                    commit = True
                else:
                    log.info(
                        "%s %s service: 'Filter Dropped Events' metric "
                        "exists; skipping.", collectorName, svc.name)

        if commit:
            ctx.commit()


ZentrapSvcDevForMsgParsing()
