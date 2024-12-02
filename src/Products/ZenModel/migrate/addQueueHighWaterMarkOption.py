##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
add --queuehighwatermark option to daemons configuration files
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")

class AddQueueHighWaterMarkOption(Migrate.Step):

    version = Migrate.Version(200, 0, 0)
    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        log.info("Updating daemons configuration files with --queuehighwatermark option.")
        commit = False
        services = filter(lambda s: all(x in s.tags for x in ["collector", "daemon"]), ctx.services)
        for svc in services:
            configfiles = svc.originalConfigs + svc.configFiles
            current_config = "/opt/zenoss/etc/%s.conf" % svc.name
            for configfile in filter(lambda f: f.name == current_config, configfiles):
                if 'maxqueuelen' in configfile.content and 'queuehighwatermark' not in configfile.content:
                    newContent = []
                    for line in configfile.content.split('\n'):
                        newContent.append(line)
                        if 'maxqueuelen' in line:
                            newContent.append('#')
                            newContent.append('# The size, in percent, of the event queue')
                            newContent.append('#  when event pushback starts, default: 0.75')
                            newContent.append('#queuehighwatermark 0.75')
                    configfile.content = "\n".join(newContent)
                    commit = True

        if commit:
            ctx.commit()


AddQueueHighWaterMarkOption()

