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


class ImportMemcachedInZauth(Migrate.Step):
    """
    Add memcached endpoint to Zauth
    """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Create the endpoint we're importing.
        memcached = sm.Endpoint(
            name = "memcached",
            purpose = "import",
            application = "memcached",
            portnumber = 11211,
            protocol = "tcp",
            addressConfig = sm.AddressConfig(0, ""),
        )

        commit = False
        zauths = filter(lambda s: s.name in ["zauth", "Zauth"], ctx.services)
        log.info("Found %i services named 'zauth' or 'Zauth'." % len(zauths))
        for zauth in zauths:
            mc_imports = filter(lambda ep: ep.name == "memcached" and ep.purpose == "import", zauth.endpoints)
            if len(mc_imports) > 0:
                log.info("Service %s already has a memcached endpoint." % zauth.name)
                continue

            log.info("Adding a memcached import endpoint to service '%s'." % zauth.name)
            zauth.endpoints.append(memcached)
            commit = True
        if commit:
            ctx.commit()

ImportMemcachedInZauth()
