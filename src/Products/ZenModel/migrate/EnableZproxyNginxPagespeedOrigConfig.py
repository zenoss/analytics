##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """EnableZproxyNginxPagespeedOrigConfig
Turns on `pagespeed` setting in Zproxy for OriginalConfig.
"""

import logging
import re
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.1.5")


class EnableZproxyNginxPagespeedOrigConfig(Migrate.Step):
    version = Migrate.Version(111, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zproxy = ctx.getTopService()

        commit = False
        config_name = "/opt/zenoss/zproxy/conf/zproxy-nginx.conf"
        try:
            config = filter(lambda conf: conf.name == config_name, zproxy.originalConfigs)[0]
        except IndexError:
            log.info("Couldn't find '%s' config.", config_name)
        else:
            config.content = re.sub(r'pagespeed off;', r'pagespeed on;', config.content)
            commit = True

        if commit:
            log.info("Committing changes.")
            ctx.commit()


EnableZproxyNginxPagespeedOrigConfig()
