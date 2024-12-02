##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Add a Description field to each Commands entry
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class AddDescriptionToCommands(Migrate.Step):

    version = Migrate.Version(106, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        topservice = ctx.getTopService()
        log.info("Found top level service: '%s'" % topservice.name)
        if topservice.name.find("Zenoss") != 0 and topservice.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        targeted = ['Imp4MariaDB', 'mariadb', 'mariadb-model', 'Zope']
        targeted_services = [service for service in ctx.services
                             if service.name in targeted]
        commit = False
        log.info("Found %i services with Commands'." % len(targeted_services))
        for service in targeted_services:
            commands = service.commands
            if not commands:
                continue
            log.info("Adding descriptions to service '%s' commands:" % service.name)
            for command in commands:
                command.description = (command.description or
                                       newDescriptions.get(command.name, ""))
                if command.description != "":
                    log.info("Command '%s' description is now '%s'." %
                             (command.name, command.description))
                commit = True

        # Commit our changes.
        if commit:
            ctx.commit()


AddDescriptionToCommands()


newDescriptions = {
    "apply-custom-patches": "Apply custom patches to the service using an installed Quilt",
    "check": "Run pre-validation prior to an Import4 import",
    "events-database": "Import events database information for Import4",
    "events-index": "Import events index information for Import4",
    "finalize": "Remove Import4 artifacts from the container",
    "help": "Display this help message",
    "import4": "Run an Import4 command",
    "initialize": "Prepare the container for Import4 and install RRDtool",
    "install-percona": "Install Percona tools",
    "install-quilt": "Install patching tool Quilt",
    "model-catalog": "Import catalog information for Import4",
    "model-database": "Import database information for Import4",
    "model-verify": "Perform post-validation of models for Import4",
    "model-zenmigrate": "Import zenmigrate information for Import4",
    "model-zenpack": "Import Zenpack information for Import4",
    "perf-abort-cleanup": "Deprecated",
    "perf-import": "Import performance data for Import4",
    "perf-verify": "Verify performance data for Import4",
    "rebuild_zodb_session": "Drop and recreate the zodb_session database",
    "reportmail": "Generate and email a report",
    "upgrade": "Upgrade a Zenoss installation",
    "zendmd": "Start an interactive zendmd session",
    "zenmib": "Load, convert, and import MIB files into the Zenoss DMD",
    "zenossdbpack": "Run Zenoss DB storage packing tool",
    "zenpack": "Check information on available Zenpacks",
    "zenpack-manager": "Install, create, link, or destroy Zenpacks"
}
