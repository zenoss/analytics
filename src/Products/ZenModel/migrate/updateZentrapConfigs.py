##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class UpdateZentrapConfigs(Migrate.Step):
    "Add zentrap.filter.conf and alter zentrap.conf."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zentraps = filter(lambda s: s.name == "zentrap", ctx.services)
        log.info("Found %i services named 'zentrap'." % len(zentraps))

        cfFilter = sm.ConfigFile (
            name = "/opt/zenoss/etc/zentrap.filter.conf",
            filename = "/opt/zenoss/etc/zentrap.filter.conf",
            owner = "zenoss:zenoss",
            permissions = "0664",
            content = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.filter.conf"), 'r').read()
        )

        for zentrap in zentraps:

            # First update zentrap.conf.
            cf = filter(lambda f: f.name == "/opt/zenoss/etc/zentrap.conf", zentrap.originalConfigs)[0]
            cf.content = open(os.path.join(os.path.dirname(__file__), "config-files", "zentrap.conf"), 'r').read()
            log.info("Updated '/opt/zenoss/etc/zentrap.conf' contents.")

            # Now add zentrap.filter.conf.
            zentrap.originalConfigs.append(cfFilter)
            log.info("Added '%s'." % cfFilter.name)

        # Commit our changes.
        ctx.commit()


UpdateZentrapConfigs()
