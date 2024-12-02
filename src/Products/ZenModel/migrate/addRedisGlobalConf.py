##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import Migrate
import servicemigration as sm


log = logging.getLogger("zen.migrate")
sm.require("1.0.0")


class AddRedisGlobalConf(Migrate.Step):
    version = Migrate.Version(200, 4, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        topService = ctx.getTopService()

        if not topService.context.get('global.conf.redis-url', None):
            topService.context['global.conf.redis-url']=u'redis://localhost:6379/0'
            log.info("global.conf.redis-url variable is added")
        if not topService.context.get('global.conf.redis-reconnection-interval', None):
            topService.context['global.conf.redis-reconnection-interval']=u'3'
            log.info("global.conf.redis-reconnection-interval variable is added")
        if not topService.context.get('global.conf.redis-graph-link-expiration', None):
            topService.context['global.conf.redis-graph-link-expiration']=u'2160'
            log.info("global.conf.redis-graph-link-expiration variable is added")
        ctx.commit()

AddRedisGlobalConf()
