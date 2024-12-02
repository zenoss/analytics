##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration import HealthCheck
sm.require("1.0.0")


class AddWebSocketHealthCheck(Migrate.Step):
    """Add `websocket_opened` healthcheck to MetricShipper service"""

    version = Migrate.Version(108,0,0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        websocket_opened_healthcheck = HealthCheck(
            name="websocket_opened",
            interval=10.0,
            script="/opt/zenoss/bin/healthchecks/MetricShipper/websocket_opened"
        )

        MetricShipper_service = filter(lambda s: s.name == "MetricShipper", ctx.services)[0]

        if not filter(lambda c: c.name == 'websocket_opened', MetricShipper_service.healthChecks):
            MetricShipper_service.healthChecks.append(websocket_opened_healthcheck)

        ctx.commit()

AddWebSocketHealthCheck()

