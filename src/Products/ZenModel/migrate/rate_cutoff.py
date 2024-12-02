##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import time
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.1.11")

class RateCutoff(Migrate.Step):
    """Fix the credentials for consumer and query services"""

    version = Migrate.Version(200, 2, 0)

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
                if "ignoreRateOption" not in configfile.content:
                    insertAfter = 'sendRateOptions:'
                    if insertAfter not in configfile.content:
                        insertAfter = 'metrics:'
                    lines = configfile.content.split('\n')
                    newLines = []
                    for line in lines:
                        newLines.append(line)
                        if insertAfter in line:
                            newLines.append('  ignoreRateOption: true')
                            newLines.append('  rateOptionCutoffTs: {{(getContext . "centralquery.ratecutoff")}}')
                    configfile.content = '\n'.join(newLines)

        parent = ctx.getTopService()
        if "centralquery.ratecutoff" not in parent.context:
            now = int(time.time() * 1000)
            parent.context["centralquery.ratecutoff"] = now

        ctx.commit()

RateCutoff()

