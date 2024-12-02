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
import re
import servicemigration as sm
from servicemigration import HealthCheck
sm.require("1.1.12")


class AddZopeDeadlockHC(Migrate.Step):
    """
    Add the deadlock healthcheck to all of the zopes.
    """

    version = Migrate.Version(200, 3, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        script_template = "curl -A '{NAME} deadlock healthcheck' --max-time 30 -s http://localhost:{PORT}/zport/ruok"
        port_pattern = ".*curl -A '([A-z]+) answering healthcheck.*localhost:([0-9]+).*"
        pattern = re.compile(port_pattern)

        commit = False
        zopes = filter(lambda s: s.name.lower() in ["zope", "zauth", "zenapi", "zendebug", "zenreports"], ctx.services)
        log.info("Found %i Zope services." % len(zopes))
        for z in zopes:
            if not filter(lambda c: c.name == 'deadlock_check', z.healthChecks):
                log.info("The {} service is missing the deadlock_check; adding it.".format(z.name))
                # we need to add the new hc.  the main problem is that the zope port changes based on which
                # type of service/tree it comes from.
                answering = filter(lambda c: c.name == 'answering', z.healthChecks)
                if not answering:
                    log.warn("Unable to find the zope answering healthcheck")
                    continue
                # grab the service name and port out of the answering healthcheck.
                answering = answering[0]
                match = pattern.match(answering.script)
                if not match:
                    log.warn("Unable to parse the zope name/port from {}: {}".format(answering.name, answering.script))
                    continue
                name = match.group(1)
                port = match.group(2)
                hc = HealthCheck(
                    name="deadlock_check",
                    script=script_template.format(NAME=name, PORT=port),
                    interval=30.0,
                    kill_count_limit=3,
                    kill_exit_codes=[28],
                )
                z.healthChecks.append(hc)
                commit = True
        if commit:
            ctx.commit()


AddZopeDeadlockHC()

