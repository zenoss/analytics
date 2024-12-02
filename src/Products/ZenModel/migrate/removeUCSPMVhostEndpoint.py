##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.1.9")


class removeUCSPMVhostEndpoint(Migrate.Step):
    "Remove one of the ucspm endpoints since it is not needed."

    version = Migrate.Version(112, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        log.info("Looking for ucspm services to migrate.")
        service = ctx.getTopService()
        if service and service.name != 'ucspm':
            log.info("Not a UCS-PM application.")
            return
        log.info("Found UCS-PM service.")

        # Remove vhost endpoint from ucspm
        commit = False
        for endpoint in service.endpoints:
            if endpoint.name == 'zproxy' and endpoint.vhostlist != None:
                filter_list = filter(lambda x: x.name != 'ucspm', endpoint.vhostlist)
                if filter_list:
                    endpoint.vhostlist = filter_list
                else:
                    endpoint.vhostlist = []
                log.info("Deleting vhost ucspm endpoint.")
                commit = True

        if commit:
            log.info("Committing changes.")
            ctx.commit()

removeUCSPMVhostEndpoint()
