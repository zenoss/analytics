##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class FixDatapointsFormat(Migrate.Step):
    """ Fix printf format for zenpop3 and zenmail datapoints format """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        servicenames = ["zenpop3", "zenmail"]
        incorrect_format = "%%d"
        correct_format = "%d"
        commit = False

        services = filter(lambda s: s.name in servicenames, ctx.services)
        graph_config = (serv.monitoringProfile.graphConfigs for serv in services)
        for graphs in graph_config:
            for graph in graphs:
                for datapoint in graph.datapoints:
                    current_format = datapoint._GraphDatapoint__data.get("format")
                    if current_format == incorrect_format:
                        datapoint._GraphDatapoint__data["format"] = correct_format
                        commit = True

        # Commit our changes.
        if commit:
            ctx.commit()

FixDatapointsFormat()

