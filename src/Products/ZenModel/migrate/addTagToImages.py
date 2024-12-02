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

class AddTagToImages(Migrate.Step):
    "Add tag latest to all Images that do not have a tag"

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        services = ctx.services

        updatedImageId = False
        for service in services:
            m = re.search("\/\S*:\w*", service.imageID)
            if service.imageID and m is None:
                log.info("Updated image id for %s" % service.name)
                service.imageID += ":latest"
                updatedImageId = True
        if updatedImageId:
            log.info("committing context with updated imageID")
            ctx.commit()

AddTagToImages()
