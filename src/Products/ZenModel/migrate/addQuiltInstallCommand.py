##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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
from servicemigration import Command
sm.require("1.0.0")


class AddQuiltInstallCommand(Migrate.Step):
    """Add `quilt-install` command to Zope service"""

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        quilt_install_command = Command('install-quilt',
                                        '${ZENHOME:-/opt/zenoss}/bin/zenrun quilt.sh install',
                                        commitOnSuccess=False)

        zope_services = filter(lambda s: s.name == "Zope", ctx.services)
        log.info("Found %i services named 'Zope'." % len(zope_services))

        for zope_service in zope_services:
            # Add `install-quilt` if it is not already present
            if not filter(lambda c: c.name == 'install-quilt', zope_service.commands):
                log.info("Added install-quilt command.")
                zope_service.commands.append(quilt_install_command)
            else:
                log.info("Install-quilt command alread present.")

        # Commit our changes.
        ctx.commit()


AddQuiltInstallCommand()

