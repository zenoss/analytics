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


class UpdateRegionServerGraphs(Migrate.Step):
    """
    Convert RegionServer operation counts graphs to display as rate.
    """
    version = Migrate.Version(200, 0, 0)

    legends = {'totalRequestCount': 'Total',
               'readRequestCount': 'Read',
               'writeRequestCount': 'Write'}

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changed = False

        regionServers = filter(lambda s: s.name == "RegionServer", ctx.services)
        for regionserver in regionServers:
            graphs = filter(lambda x: x.graphID == 'opcounts',
                                  regionserver.monitoringProfile.graphConfigs)
            if graphs:
                changed = True
                for cfg in graphs:
                    cfg.description = "Operations"
                    cfg.name = "Operations"
                    for datapoint in cfg.datapoints:
                        log.info("Updating graph: %s" % datapoint.metric)
                        datapoint.rate = True
                        datapoint.legend = "%s request rate" % self.legends[datapoint.metric]
                        datapoint.name = "%s request rate" % self.legends[datapoint.metric]

        if changed:
            ctx.commit()


UpdateRegionServerGraphs()
