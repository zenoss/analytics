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
sm.require("1.1.11")


class FixRabbitmqHealthCheck(Migrate.Step):
    """fix broken rabbitmq endpoints
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        commit = False
        for svc in ctx.services:
            rmqs = filter(
                lambda ep: ep.name == "rabbitmq" and ep.purpose == "import",
                svc.endpoints
            )
            log.info("updating a rabbitmq endpoint for service '%s'.",
                     svc.name)
            for rmq in rmqs:
                rmq.applicationtemplate = u'rabbitmq.*'
                rmq.application = u'rabbitmq.*'
                rmq.protocol = ""
                rmq.portnumber = 0

                commit = True

        if commit:
            ctx.commit()


FixRabbitmqHealthCheck()
