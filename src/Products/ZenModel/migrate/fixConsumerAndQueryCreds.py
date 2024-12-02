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

creds = """zenossCredentials:
       username: "{{(getContext . "global.conf.zauth-username")}}"
       password: "{{(getContext . "global.conf.zauth-password")}}"
"""


class FixConsumerQueryCreds(Migrate.Step):
    """Fix the credentials for consumer and query services"""

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        query_svcs = filter(lambda s: s.name == 'CentralQuery', ctx.services)
        for query_svc in query_svcs:
            configfiles = query_svc.originalConfigs + query_svc.configFiles
            for configfile in filter(lambda f: f.name == '/opt/zenoss/etc/central-query/configuration.yaml', configfiles):
                lines = configfile.content.split('\n')
                for i, line in enumerate(lines):
                    username = 'username: "$zcreds[]"'
                    password = 'password: "$zcreds[]"'
                    if username in line:
                        line = line.replace(username, 'username: "{{(getContext . "global.conf.zauth-username")}}"')
                        line = line.replace(password, 'password: "{{(getContext . "global.conf.zauth-password")}}"')
                        lines[i] = line
                configfile.content = '\n'.join(lines)

        consumer_svcs = filter(lambda s: s.name == 'MetricConsumer', ctx.services)
        for consumer_svc in consumer_svcs:
            configfiles = consumer_svc.originalConfigs + consumer_svc.configFiles
            for configfile in filter(lambda f: f.name == '/opt/zenoss/etc/metric-consumer-app/configuration.yaml', configfiles):
                if 'zenossCredentials' not in configfile.content:
                    configfile.content = configfile.content + creds
        ctx.commit()


FixConsumerQueryCreds()
