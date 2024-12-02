##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
In 5.0, the 'ready' healthcheck for the tenant application expected the HTML
returned for a 401 error to contain the word 'zope', which happened to be
included in the stacktrace output returned by Zope in the HTML page for 401
errors. The stacktrace was removed as part of cleaning up a security bug in
Zope, and that broke the healthcheck.

This script updates the 'ready' healthcheck for tenant apps so that it just
checks the HTTP status code. Presumably, if Zope can respond to an
unauthenticated request with a 401, it is ready to accept other requests.
"""

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class FixZopeHealthCheck(Migrate.Step):
    "Change 'ready' healthcheck to only look at HTTP status code"

    version = Migrate.Version(5,0,70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Get all toplevel applications that start with Zenoss or USC-PM
        service = ctx.getTopService()
        log.info("Found top level service: '%s'" % service.name)
        if service.name.find("Zenoss") != 0 and service.name.find("UCS-PM") != 0:
            log.info("Top level service name isn't Zenoss or UCS-PM; skipping.")
            return

        # Update all of the 'ready' healthchecks
        readyHealthChecks = filter(lambda healthCheck: healthCheck.name == "ready", service.healthChecks)
        log.info("Found %i 'ready' healthchecks'." % len(readyHealthChecks))
        for readyCheck in readyHealthChecks:
            readyCheck.script = "curl --output /dev/null --silent --write-out \"%{http_code}\" http://localhost:8080/robots.txt | grep 200 >/dev/null"
            log.info("Updated 'ready' healthcheck.")

        ctx.commit()

FixZopeHealthCheck()
