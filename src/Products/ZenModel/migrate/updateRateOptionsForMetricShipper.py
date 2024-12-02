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
sm.require("1.1.10")



class UpdateRateOptionsForMetricShipper(Migrate.Step):
    """
    Update/Add rateOptions for counters.
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = filter(lambda s: s.name in ["MetricShipper"], ctx.services)
        log.info("Found {0} services named 'MetricShipper'.".format(len(services)))

        changed = False
        for svc in services:
            mprofile = svc.monitoringProfile
            for gconfig in mprofile.graphConfigs:
                for dp in gconfig.datapoints:
                    if dp.rate == True:
                        changed = True
                        dp.rateOptions = {
                            "counter": True
                        }
                        log.info("[{0}] {1}.rateOptions set to {2}".format(svc.name, dp.name, dp.rateOptions))

        if changed:
            ctx.commit()

UpdateRateOptionsForMetricShipper()
