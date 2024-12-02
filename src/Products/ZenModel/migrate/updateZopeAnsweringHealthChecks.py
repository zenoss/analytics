##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
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


class UpdateZopeAnsweringHealthChecks(Migrate.Step):
    """
    Change zope and zauth 'answering' healthcheck to hit a
    lighter weight zope url to reduce unnecessary load on zope,
    and change zproxy 'answering' healthcheck to use a preexisting
    healthcheck script
    """

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # find zproxy
        zproxy = ctx.getTopService()
        zproxyNameLower = zproxy.name.lower()
        if all(["zenoss" not in zproxyNameLower,
                "ucs-pm" not in zproxyNameLower,
                "nfvi" not in zproxyNameLower]):
            log.info("Skipping migration for %s" % zproxy.name)
            return

        log.info("Found top level service: '%s'" % zproxy.name)

        # Update the zproxy 'answering' healthcheck
        hcs = [h for h in zproxy.healthChecks if h.name == "answering"]
        for hc in hcs:
            hc.script = "/opt/zenoss/bin/healthchecks/zproxy_answering"
            log.info("Updated 'answering' healthcheck for %s" % zproxy.name)

        # find one or more zopes
        zopides = []
        for s in ctx.services:
            if s.name.lower() == "zope":
                zopides.append(s)

        # Update the zope 'answering' healthcheck
        for zope in zopides:
            hcs = [h for h in zope.healthChecks if h.name == "answering"]
            for hc in hcs:
                hc.script = "curl --retry 3 --max-time 2 -s http://localhost:9080/zport/ruok | grep -q imok"
                log.info("Updated 'answering' healthcheck for Zope")

        # find one or more zauths
        zauths = []
        for s in ctx.services:
            if s.name.lower() == "zauth":
                zauths.append(s)

        # Update the zauth 'answering' healthcheck
        for zauth in zauths:
            hcs = [h for h in zauth.healthChecks if h.name == "answering"]
            for hc in hcs:
                hc.script = "curl -s http://localhost:9180/zport/ruok | grep -q imok"
                log.info("Updated 'answering' healthcheck for zauth")

        ctx.commit()

UpdateZopeAnsweringHealthChecks()
