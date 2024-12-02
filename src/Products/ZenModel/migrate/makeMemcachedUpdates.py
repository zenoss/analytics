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


class MakeMemcachedUpdates(Migrate.Step):
    """
    Update memcache healthcheck, and add the service to Core
    """

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcacheds = filter(lambda s: s.name == "memcached", ctx.services)
        log.info("Found %i services named 'memcached'" % len(memcacheds))
        if not memcacheds:
            log.info("Couldn't find memcached service, skipping.")
            return

        commit = False
        for memcached in memcacheds:
            answering = filter(lambda hc: hc.name == 'answering', memcached.healthChecks)
            if answering:
                answering[0].script = "{ echo stats; sleep 1; } | nc 127.0.0.1 11211 | grep -q uptime"
                commit = True
                log.info("Updated 'answering' healthcheck.")
            else:
                log.info("Could not find 'answering' healthcheck to update.")

            # Create /etc/sysconfig/memcached if it doesn't exist
            esm_content = """\
PORT="11211"
USER="memcached"
MAXCONN="1024"
CACHESIZE="{{.RAMCommitment}}"
OPTIONS=""
    """
            e_s_memcached = sm.ConfigFile (
                name = "/etc/sysconfig/memcached",
                filename = "/etc/sysconfig/memcached",
                owner = "zenoss:zenoss",
                permissions = "0664",
                content = esm_content,
            )
            if '/etc/sysconfig/memcached' not in [cf.name for cf in memcached.originalConfigs]:
                memcached.originalConfigs.append(e_s_memcached)
                log.info("Added '/etc/sysconfig/memcached'")
                commit = True

        if commit:
            ctx.commit()

MakeMemcachedUpdates()
