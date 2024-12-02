##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = """
Set pagespeed on in zproxy-nginx.conf
"""
import logging
import re

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")

class EnableNginxPagespeed(Migrate.Step):
    '''
    Turn pagespeed in zproxy-nginx.conf
    '''

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping")
            return

        commit = False
        zproxy = ctx.getTopService()
        log.info("Top-level service is '{}'.".format(zproxy.name))
        configfiles = zproxy.originalConfigs + zproxy.configFiles
        for config_file in filter(lambda f: f.name == '/opt/zenoss/zproxy/conf/zproxy-nginx.conf', configfiles):
            config_text = config_file.content

            pgspeed_setting = re.search("pagespeed on", config_text)
            if pgspeed_setting is not None:
                continue

            config_text = re.sub('pagespeed off', "pagespeed on", config_text)

            log.info("Turning pagespeed on for {} and {}".format(config_file.name, zproxy.name))
            config_file.content = config_text
            commit = True

        if commit:
            ctx.commit()


EnableNginxPagespeed()
