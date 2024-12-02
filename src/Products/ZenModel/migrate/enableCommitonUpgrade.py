##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Set Zenoss upgrade CommitOnSuccess to True
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class EnableCommitOnUpgrade(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Update the zope service commands.
        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        if len(zopes) != 1:
            log.info("Found %i services named 'Zope'; skipping." % len(zopes))
            return
        upgrades = filter(lambda c: c.name == "upgrade", zopes[0].commands)
        for command in upgrades:
            command.commitOnSuccess = True
            log.info("Set commitOnSuccess=True for 'upgrade'.")
        ctx.commit()


EnableCommitOnUpgrade()
