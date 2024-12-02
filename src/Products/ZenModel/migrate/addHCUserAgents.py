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

sm.require("1.0.0")

class AddHCUserAgents(Migrate.Step):
    """
    Adds a user-agent string to curl-based healthchecks.

    There are a lot of unique healthchecks, so each one
    is named by capturing the name of the service and the name
    of the healthcheck.

    """

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        healthchecked = filter(lambda s: s.healthChecks, ctx.services)

        updated = 0
        commit = False
        for service in healthchecked:
            for hc in service.healthChecks:
                script = hc.script
                if 'curl ' in script:
                    if "curl -A" in script:
                        # User-agent already specified.
                        continue
                    useragent = '%s %s healthcheck' % (service.name, hc.name)
                    script = script.replace('curl', "curl -A '%s'" % useragent)
                    hc.script = script
                    msg = ("Added user-agent string to %s %s healthcheck." %
                           (service.name, hc.name))
                    log.info(msg)
                    updated += 1

        if updated:
            log.info("%i healthcheck(s) modified by addHCUserAgents." % updated)
            ctx.commit()
        else:
            log.info("No healthchecks modified by addHCUserAgents.")

AddHCUserAgents()
