##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
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



class UpdateZenactiondConfig(Migrate.Step):
    "Add strip-email-body-tags option"

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zenactiond = filter(lambda s: s.name == "zenactiond", ctx.services)[0]
        update = ('\n# Strip HTML/XML tags from plaintext'
                  '\n# email notifications?'
                  '\n#strip-email-body-tags True\n#\n')

        cfg = filter(lambda f: f.name == "/opt/zenoss/etc/zenactiond.conf", zenactiond.originalConfigs)[0]
        if cfg.content.find("strip-email-body-tags") < 0:
            cfg.content += update
            log.info("Added strip-email-body-tags option")
            ctx.commit()

UpdateZenactiondConfig()
