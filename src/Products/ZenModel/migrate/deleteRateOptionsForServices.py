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

sm.require("1.1.11")


class DeleteRateOptionsForServices(Migrate.Step):
    """
    Update/Add rateOptions for counters.
    Remove reset values.
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        metrics = ("dataPoints", "eventCount", "missedRuns")


        daemons = filter(lambda s: 'daemon' in s.tags and 'collector' in s.tags, ctx.services)
        hubs = filter(lambda s: 'daemon' in s.tags and 'hub' in s.tags, ctx.services)

        def updateMetricConfig(metricConfigs, metricIDs):
            changed = False
            for mconfig in metricConfigs:
                for metric in mconfig.metrics:
                    if metric.counter == True and metric.ID in metricIDs:
                        changed = True
                        metric.counter = False
                        log.info("[{0}] metric config for {1} set to rate to False".format(svc.name, metric.ID))
            return changed

        def updateGraphConfigs(graphConfigs, metricNames):
            changed = False
            for gconfig in mprofile.graphConfigs:
                for dp in gconfig.datapoints:
                    if dp.rate == True and dp.metric in metricNames:
                        changed = True
                        dp.rate = False
                        dp.rateOptions = None
                        log.info("[{0}] graph config rate for {1} set to False".format(svc.name, dp.name))
            return changed
        
        changed = False
        for svc in daemons:
            mprofile = svc.monitoringProfile
            if updateGraphConfigs(mprofile.graphConfigs, metrics):
                changed = True
            if updateMetricConfig(mprofile.metricConfigs, metrics):
                changed = True

        for svc in hubs:
            mprofile = svc.monitoringProfile
            if updateMetricConfig(mprofile.metricConfigs, ['invalidations']):
                changed = True

        if changed:
            ctx.commit()


DeleteRateOptionsForServices()

