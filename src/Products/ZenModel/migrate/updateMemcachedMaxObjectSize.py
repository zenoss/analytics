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

class UpdateMemcachedMaxObjectSize(Migrate.Step):
    """
    Update memcached service def to include a default value for the max object size
    that memcached clients can send
    """

    version = Migrate.Version(108, 0, 0)

    OPTIONS_TEXT = '''{{ $size := (getContext . "global.conf.zodb-cache-max-object-size") }}
OPTIONS="-v -R 4096 -I {{if $size}} {{$size}} {{else}} 1048576 {{end}}"'''

    SEARCH_TEXT = OPTIONS_TEXT[:70]

    def _update_config(self, config):
        changed = False
        if self.SEARCH_TEXT not in config.content:
            new_content = []
            for line in config.content.split("\n"):
                if line.startswith("OPTIONS="):
                    new_content.append(self.OPTIONS_TEXT)
                    changed = True
                else:
                    new_content.append(line)
            if changed:
                config.content = "\n".join(new_content)
        return changed

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return
        zenoss = ctx.getTopService()
        memcached = filter(lambda x: x.name=="memcached", ctx.services)
        if memcached:
            memcached = memcached[0]
            configs = [ cfg for cfg in memcached.originalConfigs if cfg.name == '/etc/sysconfig/memcached' ]
            if hasattr(memcached, "configFiles"):
                configs.extend( [ cfg for cfg in memcached.configFiles if cfg.name == '/etc/sysconfig/memcached' ] )
            commit = False
            for config in configs:
                if self._update_config(config):
                    log.info("/etc/sysconfig/memcached updated.")
                    commit = True
            if commit:
                ctx.commit()


UpdateMemcachedMaxObjectSize()
