##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
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


class zenmodelerWorkers(Migrate.Step):
    "Add worker options to zenmodeler."

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        # Don't apply this migration to core.
        if dmd.getProductName() == "core":
            return

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all zenmodeler services.
        modelers = filter(lambda s: s.name == "zenmodeler", ctx.services)
        log.info("Found %i services named 'zenmodeler'." % len(modelers))

        # Alter their startup command and instanceLimits.
        for modeler in modelers:
            modeler.startup = "su - zenoss -c \"/opt/zenoss/bin/zenmodeler run -c --logfileonly --workers {{.Instances}} --workerid $CONTROLPLANE_INSTANCE_ID --monitor {{(parent .).Name}} \""
            modeler.instanceLimits.minimum = 1
            modeler.instanceLimits.maximum = None
            log.info("Updated startupcommand, set instance minimum to 1, and instance maximum to None.")

        # Commit our changes.
        ctx.commit()


zenmodelerWorkers()
