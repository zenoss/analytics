##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import re
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm

sm.require("1.1.5")

class AddToolboxLogsToKibana(Migrate.Step):
    "Pull logs provided by toolbox utilities to logstash."

    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return


        log_paths = dict(
                        zodbscan="/opt/zenoss/log/toolbox/zodbscan.log",
                        zennetworkclean="/opt/zenoss/log/toolbox/zennetworkclean.log",
                        zenindextool="/opt/zenoss/log/toolbox/zenindextool.log",
                        zencheckdbstats="/opt/zenoss/log/toolbox/zencheckdbstats.log",
                        zencatalogscan="/opt/zenoss/log/toolbox/zencatalogscan.log",
                        findposkeyerror="/opt/zenoss/log/toolbox/findposkeyerror.log",
                        zenrelationscan="/opt/zenoss/log/toolbox/zenrelationscan.log"
        )

        new_logs = []
        for name in log_paths.keys():
            logType = "toolbox_{0}_logs".format(name)
            new_logs.append(sm.logconfig.LogConfig(
                                 path=log_paths[name],
                                 logType=logType,
                                 filters=['pythondaemon'],
                                 logTags=None, isAudit=False))

        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        changed = False
        for zope in zopes:
            for new_log in new_logs:
                # ZEN-28564 prevent UnboundLocalError by renaming log into log_
                if new_log.path not in [log_.path for log_ in zope.logConfigs]:
                    zope.logConfigs.append(new_log)
                    changed = True

        if changed:
            ctx.commit()

AddToolboxLogsToKibana()
