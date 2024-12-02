##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
import servicemigration.thresholdconfig
import servicemigration.threshold
import servicemigration.eventtags

sm.require("1.1.6")

class addMissedRunsThreshold(Migrate.Step):
    """Adds a threshold for missedRuns for collector services"""

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate context, skipping.")
            return

        # Get all collector services
        changed = False
        collectors = filter(lambda s: "collector" in s.tags, ctx.services)
        for service in collectors:
            for graph_config in service.monitoringProfile.graphConfigs:
                metric_source = ""
                # Get the metric source from the graphconfig
                if graph_config.graphID == "missedRuns":
                    for datapoint in graph_config.datapoints:
                        if datapoint.pointID == "missedRuns":
                            metric_source = datapoint.metricSource
                    has_threshold = False
                    # Skip this service if we already have the threshold
                    for threshold in service.monitoringProfile.thresholdConfigs:
                        if threshold.thresholdID == "missedRuns.high":
                            has_threshold = True
                            break
                    if not has_threshold:
                        thresh = sm.threshold.Threshold(
                            thresholdMax="5"
                        )
                        event_tags = sm.eventtags.EventTags(
                            severity=3,
                            resolution="Add more collectors",
                            explanation="This service is missing runs",
                            eventClass="/App/Zenoss"
                        )
                        tc = sm.thresholdconfig.ThresholdConfig(
                            thresholdID="missedRuns.high",
                            name="Missed Runs High",
                            description="High number of missed runs",
                            metricSource=metric_source,
                            datapoints=["missedRuns"],
                            thresholdType="MinMax",
                            threshold=thresh,
                            eventTags=event_tags
                        )
                        service.monitoringProfile.thresholdConfigs.append(tc)
                        changed = True
                        break

        if changed:
            # Commit our changes
            ctx.commit()

addMissedRunsThreshold()
