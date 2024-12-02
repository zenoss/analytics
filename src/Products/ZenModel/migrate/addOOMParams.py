##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm

from pkg_resources import parse_version
from Products.ZenUtils.controlplane.client import getCCVersion

log = logging.getLogger("zen.migrate")
sm.require("1.1.13")


class AddOOMParams(Migrate.Step):
    "Add OOMKillDisable and OOMScoreAdj parameters to db services"

    version = Migrate.Version(200, 4, 0)

    def cutover(self, dmd):
        cc_version = parse_version(getCCVersion())
        if cc_version < parse_version("1.6.5"):
            log.info("Require CC version >= 1.6.5, skipping")
            return

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        service_names = ['mariadb-model', 'redis', 'RegionServer', 'ZooKeeper',
                         'HMaster', 'Impact', 'Solr', 'mariadb-events']
        services = filter(lambda s: s.name in service_names, ctx.services)
        log.info("Found %i services", len(services))

        for service in services:
            service.oomKillDisable = True
            service.oomScoreAdj = 0
        ctx.commit()

AddOOMParams()
