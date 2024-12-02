##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class ChangeMemcachedStartup(Migrate.Step):
    "Change memcached startup to respect config file and update config file"

    version = Migrate.Version(108, 0, 0)

    def _update_config(self, config):
        USER_RE = r'USER="\w+"'
        CACHESIZE_RE = r'CACHESIZE="{{[\w.]+}}"'
        OPTIONS_RE = r'OPTIONS="\w*"'

        USER = 'USER="nobody"'
        CACHESIZE = 'CACHESIZE="{{percentScale .RAMCommitment 0.9 | bytesToMB}}"'
        OPTIONS = 'OPTIONS="-v -R 4096"'

        config = re.sub(USER_RE, USER, config, 0, re.MULTILINE)
        config = re.sub(CACHESIZE_RE, CACHESIZE, config, 0, re.MULTILINE)
        config = re.sub(OPTIONS_RE, OPTIONS, config, 0, re.MULTILINE)
        return config

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        memcached_services = filter(lambda cf: cf.name == 'memcached', ctx.services)

        for service in memcached_services:
            service.startup = "${ZENHOME:-/opt/zenoss}/bin/zenmemcached"

            cfs = filter(lambda cf: cf.name == "/etc/sysconfig/memcached",
                         service.originalConfigs + service.configFiles)
            for cf in cfs:
                cf.content = self._update_config(cf.content)

        ctx.commit()


ChangeMemcachedStartup()
