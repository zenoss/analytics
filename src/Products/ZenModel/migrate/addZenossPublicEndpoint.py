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
from servicemigration.vhost import VHost
sm.require("1.1.9")



class AddZenossPublicEndpoint(Migrate.Step):
    """
    Add public endpoint ("zenoss") to zproxy.
    """

    version = Migrate.Version(200, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        top = ctx.getTopService()        
        zproxy = next((endpoint for endpoint in top.endpoints if endpoint.name == "zproxy"), None)
        if not zproxy:
            log.info("Endpoints for zproxy not found, skipping.")
        else:            
            if any(vhost for vhost in zproxy.vhostlist if vhost.name == "zenoss5"):
                if not any(vhost for vhost in zproxy.vhostlist if vhost.name == "zenoss"):
                    zproxy.vhostlist.append(
                        VHost(name="zenoss", enabled=False)
                    )
                    ctx.commit()                    
                    log.info("Public endpoint 'zenoss' for zproxy was added.")
                else:
                    log.info("Public endpoint 'zenoss' already exists, skipping.")
            else:
                log.info("Public endpoint 'zenoss5' not found, skipping.")        

AddZenossPublicEndpoint()
