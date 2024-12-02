##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """ChangeDefaultZauthZserverThreads

Adds a zodb object that is a collection of user configurable settings
that affect the behavior of the User Interface.
"""

import logging
import re
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.1.5")


class ChangeDefaultZauthZserverThreads(Migrate.Step):
    version = Migrate.Version(111, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zauths = filter(lambda s: s.name == "Zauth", ctx.services)
        if not zauths:
            log.info("Couldn't find Zauth service, skipping.")
            return
        log.info("Found Zauth service.")

        commit = False
        for service in zauths:
            zauthZopeConfs = filter(lambda config: config.name.endswith("zauth-zope.conf"), service.configFiles)
            for config in zauthZopeConfs:
                config.content = re.sub(r'zserver-threads \d+', r'zserver-threads 7', config.content)
                commit = True

        if commit:
            log.info("Committing changes.")
            ctx.commit()


ChangeDefaultZauthZserverThreads()
