##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class RemoveRegionServerPrereqs(Migrate.Step):

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        regionServers = filter(lambda x: x.name == 'RegionServer', ctx.services)
        commit = False
        for server in regionServers:
            server.prereqs = []
            commit = True
        if commit:
            log.info("Prereqs for RegionServer updated.")
            ctx.commit()

RemoveRegionServerPrereqs()
